# 🤖 Cardputer Gemini Chat App

This is a MicroPython application for the M5Stack Cardputer, enabling a simple chat interface with the Google Gemini AI model (specifically `gemini-2.5-flash-lite`). It's designed to be a friendly assistant for children aged 10-12, providing short, clear responses.

---

## ✨ Features

* **Direct Input:** Type your messages right on the Cardputer's screen.

* **Child-Friendly AI:** The Gemini model is prompted to act as a helpful and simple assistant for kids.

* **Limited Responses:** AI replies are kept to one or two short sentences for clarity and readability on the small screen.

* **Conversation History:** The app maintains a short history of your chat with the AI (last 5 turns) for context.

* **Wi-Fi Connection:** Automatically connects to your Wi-Fi network configured on the Cardputer.

* **Error Handling:** Provides on-screen pop-ups for network or API issues.

---

## 🚀 Setup & Installation

1.  **MicroPython Firmware:** Ensure your M5Stack Cardputer has MicroPython firmware installed.

2.  **Dependencies:** This app uses standard MicroPython libraries and specific `lib/hydra` libraries found in the MicroHydra launcher environment. Make sure these are available on your device.

3.  **API Key:** You need a Gemini API key from the Google AI Studio.

    * **Configure your API key:** On your Cardputer, access the system configuration (often via a `config.json` file or similar mechanism within the MicroHydra launcher). Add your Gemini API key under the key `gemini_api_key`.

    * You'll also need to configure your **Wi-Fi credentials**: `wifi_ssid` and `wifi_pass` in the same configuration.

    *Example `config.json` snippet (your actual config location/method may vary):*

    ```
    {
        "wifi_ssid": "YourWiFiNetworkName",
        "wifi_pass": "YourWiFiPassword",
        "gemini_api_key": "YOUR_GEMINI_API_KEY_HERE"
    }
    ```

4.  **Upload App:**

    * Save the provided MicroPython code as `__init__.py`.

    * Create a folder under `/apps/` (e.g., `/apps/gemini_chat/`).

    * Upload `__init__.py` into this folder: `/apps/gemini_chat/__init__.py`.

---

## 🎮 How to Use

1.  **Launch the App:** Navigate to the "Gemini Chat" app (or whatever you named the folder) in your Cardputer's MicroHydra launcher.

2.  **Wi-Fi Connection:** The app will attempt to connect to Wi-Fi automatically.

3.  **Type Your Message:**

    * Start typing directly on the Cardputer's keyboard. Your input will appear in the "Input:" line at the bottom of the screen.

    * Use the **Backspace (BS)** key to delete characters.

    * Use the **Space (SPC)** key for spaces.

4.  **Send Message:** Press the **Enter (ENT)** key to send your message to the Gemini AI.

5.  **View Response:** The AI's response will appear in the chat history above your input line.

6.  **Continue Chatting:** After the AI responds, the input line will be ready for your next message.

7.  **Exit App:** Press the **ESC** key to exit the application.

---

## ⚠️ Notes & Troubleshooting

* **Memory Usage:** The Cardputer has limited memory. Keeping the AI responses short and the conversation history sent to the API limited helps prevent out-of-memory errors.

* **Network Stability:** A stable Wi-Fi connection is crucial for the app to function correctly. Error messages will appear if there are network issues.

* **API Key Errors (HTTP 400):** If you see `HTTP Error: 400`, it often means the API request is malformed or too large. The app tries to mitigate this by limiting conversation history. Ensure your API key is correctly configured.

* **Display Issues:** If text appears truncated or overflows, the `wrap_text` function might need adjustments, or the input might be excessively long.
