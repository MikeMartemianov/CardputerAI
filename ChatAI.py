import json
import requests
import network # Import network module for Wi-Fi
import time # Import time for potential sleep_ms
from lib.display import Display
from lib.userinput import UserInput
from lib.hydra import popup, beeper, config
from lib.device import Device

# --- Globals ---
# Use use_tiny_buf=True for memory efficiency
d = Display(use_tiny_buf=True)
kb = UserInput()
ov = popup.UIOverlay()
b = beeper.Beeper()
cfg = config.Config()

W, H = Device.display_width, Device.display_height
# Model name
MODEL_NAME = "gemini-2.5-flash-lite"
# Non-streaming API endpoint
API_URL_BASE = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key="

# Stores conversation history for API
conversation = []
# Max number of conversation turns to send to the API (user + model pairs)
MAX_CONVERSATION_HISTORY = 5 # Keep last 5 user/model pairs + current user message

# System prompt for the AI model
# This tells the AI how to behave (in English, as per request)
SYSTEM_PROMPT = {
    "role": "user",
    "parts": [{"text":
               "You are a helpful and friendly assistant designed for children aged 10-12, running on very small device M5 CardPuter. Use simple language and explain things clearly. Answer in one short sentense."}]
}

# --- Functions ---

def connect_wifi():
    """Connects to Wi-Fi using credentials from config."""
    print("WiFi: Attempting to connect...")
    nic = network.WLAN(network.STA_IF)
    if not nic.active():
        nic.active(True)

    ssid = cfg['wifi_ssid']
    password = cfg['wifi_pass']

    if not ssid or not password:
        print("WiFi: Missing 'wifi_ssid' or 'wifi_pass' in config!")
        ov.error("No WiFi credentials!")
        time.sleep(3) # Display error for a few seconds
        ov.close()
        return False

    if nic.isconnected():
        print(f"WiFi: Already connected to {ssid}")
        return True

    # Try connecting
    nic.connect(ssid, password)
    max_retries = 20 # ~10 seconds with 500ms sleep
    retries = 0

    d.text("Connecting WiFi...", 2, H - 10, d.palette[9])
    d.show()

    while not nic.isconnected() and retries < max_retries:
        time.sleep_ms(500)
        retries += 1
        d.text(f"Connecting WiFi... {retries}", 2, H - 10, d.palette[9])
        d.show()
        print(f"WiFi: Connecting... attempt {retries}")
    
    # Clear "Connecting WiFi" message
    d.rect(0, H - 10, W, 10, d.palette[2], fill=True)
    d.show()

    if nic.isconnected():
        print(f"WiFi: Connected! IP: {nic.ifconfig()[0]}")
        return True
    else:
        print("WiFi: Failed to connect.")
        ov.error("WiFi connection failed!")
        time.sleep(3) # Display error for a few seconds
        ov.close()
        return False

def wrap_text(text, width):
    """Wraps text into lines based on pixel width."""
    lines = []
    current_line = ""
    # Ensure text is treated as a string before splitting
    text_str = str(text) 
    for word in text_str.split(' '):
        # Handle cases where a single word might be longer than the line width
        word_width = d.get_total_width(word)
        if word_width > width:
            # If a single word is too long, break it into parts that fit
            temp_word_part = ""
            for char in word:
                if d.get_total_width(temp_word_part + char) <= width:
                    temp_word_part += char
                else:
                    if temp_word_part: lines.append(temp_word_part)
                    temp_word_part = char # Start new part with the current char
            if temp_word_part: lines.append(temp_word_part) # Add any remaining part
            current_line = "" # Reset current_line after handling long word
            continue

        if d.get_total_width(current_line + (' ' if current_line else '') + word) <= width:
            current_line += (' ' if current_line else '') + word
        else:
            if current_line: lines.append(current_line.strip())
            current_line = word
    if current_line: lines.append(current_line.strip())
    return lines

def draw_ui():
    """Renders the chat interface: history and hints."""
    d.rect(0, 0, W, H, d.palette[2], fill=True) # Clear screen
    # Shortened name for UI
    d.text(f"Model: Flash-Lite", 2, 2, d.palette[9]) 
    d.line(0, 12, W, 12, d.palette[8])

    y = H - 4
    # Draw history from bottom up, excluding the SYSTEM_PROMPT if it's there
    # The actual conversation history starts after the SYSTEM_PROMPT
    display_conversation = [entry for entry in conversation if entry != SYSTEM_PROMPT]

    for entry in reversed(display_conversation): 
        role = entry['role']
        # Use d.palette[13] (blue-ish) for bot's text
        color = d.palette[10] if role == 'user' else d.palette[13] 
        prefix = "You: " if role == 'user' else "Bot: "
        
        # Ensure 'text' part exists before accessing
        if 'text' in entry['parts'][0]:
            lines = wrap_text(prefix + entry['parts'][0]['text'], W - 4)
            for line in reversed(lines):
                y -= 10
                if y < 14: break
                d.text(line, 2, y, color)
            if y < 14: break
            
    d.show()

def call_gemini_api(api_key):
    """Sends a request and handles the full response, updating the UI."""
    # Ensure WiFi is connected before making an API call
    if not network.WLAN(network.STA_IF).isconnected():
        print("API: WiFi not connected, attempting to reconnect...")
        if not connect_wifi():
            ov.error("API: No network!")
            time.sleep(3) # Display error for a few seconds
            ov.close()
            return

    print("API: Starting request.")
    # Add a placeholder for the model's response
    bot_response_entry = {"role": "model", "parts": [{"text": ""}]}
    
    # Prepare conversation history for the API call
    # Always include the SYSTEM_PROMPT at the very beginning of the payload_contents
    payload_contents = [SYSTEM_PROMPT] # Start with the system prompt

    # Limit history to MAX_CONVERSATION_HISTORY user-bot pairs + current user message
    # We take the actual conversation (excluding the initial SYSTEM_PROMPT if it was ever added locally)
    # and then add the relevant recent turns.
    actual_conversation_for_history = [entry for entry in conversation if entry != SYSTEM_PROMPT]
    start_index = max(0, len(actual_conversation_for_history) - MAX_CONVERSATION_HISTORY * 2)
    payload_contents.extend(actual_conversation_for_history[start_index:]) 

    # We need to append the placeholder for the bot's response to the *local* conversation
    # immediately, so draw_ui() can render it as "Bot: " while fetching.
    conversation.append(bot_response_entry)

    headers = {'Content-Type': 'application/json'}
    # The payload sent to the API contains the limited history *without* the empty bot_response_entry
    # (as the API generates it).
    
    # Add generationConfig to limit output length
    payload = json.dumps({
        "contents": payload_contents,
        "generationConfig": {
            "maxOutputTokens": 50 # Roughly 1-2 short sentences
        }
    })
    
    print(f"API: Payload size: {len(payload)} bytes")
    
    try:
        url = API_URL_BASE + api_key
        r = requests.post(url, headers=headers, data=payload) 

        if r.status_code != 200:
            err_msg = f"HTTP Error: {r.status_code}"
            try: # Try to read error message from content if available
                err_content = r.content.decode('utf-8')
                if err_content: err_msg += f" - {err_content[:50]}" # Limit length
            except:
                pass
            print(f"API: {err_msg}")
            ov.error(err_msg)
            time.sleep(3) # Display error for a few seconds
            ov.close()
            conversation.pop() # Remove the empty bot response entry
            r.close()
            return

        # Process the full response
        try:
            data = json.loads(r.content.decode('utf-8'))
            # Check for 'candidates' and 'parts' before accessing
            if 'candidates' in data and len(data['candidates']) > 0 and \
               'content' in data['candidates'][0] and \
               'parts' in data['candidates'][0]['content'] and \
               len(data['candidates'][0]['content']['parts']) > 0 and \
               'text' in data['candidates'][0]['content']['parts'][0]:
                
                full_text_response = data['candidates'][0]['content']['parts'][0]['text']
                bot_response_entry['parts'][0]['text'] = full_text_response # Assign full text
                b.play(("C7",), 10, 2) # Play sound once after full response
                draw_ui()
            else:
                print("API: Unexpected response structure.")
                ov.error("Bad API Response")
                time.sleep(3) # Display error for a few seconds
                ov.close()
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            print(f"API: Error parsing full JSON response: {e}, Content: {r.content.decode('utf-8')[:100]}")
            ov.error("JSON Parse Error")
            time.sleep(3) # Display error for a few seconds
            ov.close()
        
        r.close() # Close the response connection
        print("API: Request finished.")
    except Exception as e:
        print(f"API: Request failed with exception: {e}")
        ov.error(f"Request Fail: {e}")
        time.sleep(3) # Display error for a few seconds
        ov.close()
        if conversation: conversation.pop() # Remove the empty bot response entry

def main():
    """Main application loop."""
    print("App: Starting.")
    d.rect(0,0,1,1,d.palette[2]); d.show()

    # Access config value using dictionary-style access
    api_key = cfg['gemini_api_key'] 
    if not api_key:
        print("App: Error - gemini_api_key not found in config!")
        ov.error("Set gemini_api_key in config!")
        time.sleep(3) # Display error for a few seconds
        ov.close()
        return

    # Attempt to connect to WiFi at startup
    if not connect_wifi():
        print("App: Initial WiFi connection failed. Continuing without network access.")
    
    draw_ui()

    should_prompt_next = True # Flag to control when to open text_entry

    while True:
        if should_prompt_next:
            current_prompt = ov.text_entry("")
            should_prompt_next = False # Reset flag after attempting to prompt

            if current_prompt is None: # User pressed ESC within text_entry
                print("App: User cancelled text entry. Now waiting for manual ENT or ESC.")
                # should_prompt_next remains False, so it won't auto-open next loop iteration
            elif current_prompt: # User entered text and pressed ENT
                print(f"App: User input received: '{current_prompt}'")
                # Add user message to conversation *before* calling API
                # The actual system prompt is added only to the API payload, not the display conversation
                conversation.append({"role": "user", "parts": [{"text": current_prompt}]})
                draw_ui() # Redraw UI with user's message
                call_gemini_api(api_key)
                should_prompt_next = True # Prompt again after bot response
            else: # User pressed ENT but input was empty
                print("App: Empty message entered. Prompting again immediately.")
                should_prompt_next = True # Stay in prompt mode for next loop iteration
        
        # Always check for system-wide keys (like ESC for exiting the app)
        for k in kb.get_new_keys():
            if k == "ESC":
                print("App: ESC pressed, exiting.")
                raise SystemExit
            # If the app is not currently in auto-prompt mode (user cancelled the last one)
            # and ENT is pressed, trigger the prompt for the next iteration.
            if k == "ENT" and not should_prompt_next: 
                print("App: ENT pressed (outside auto-prompt), triggering prompt.")
                should_prompt_next = True # Force prompt next iteration
        
        time.sleep_ms(20) # Small delay to prevent busy-looping

main()

