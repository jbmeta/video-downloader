# Video Downloader

![Python Version](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

A simple, user-friendly desktop application built with Flask and FlaskUI to download videos from Twitter (now X.com) directly to your computer. Just paste a tweet URL, select your desired resolution, and download!

## ✨ Features

* **Clean and Intuitive UI:** Easy-to-use interface for quick video downloads.
* **Twitter/X.com Support:** Downloads videos directly from tweet URLs.
* **Resolution Selection:** Choose from available video resolutions.
* **Automatic Cleanup:** Temporarily downloaded files are automatically cleaned up after streaming to the user.
* **Standalone Executable:** Package the application into a single executable file for easy distribution and use without Python installation.
* **Custom Icon:** Brand your application with a custom icon for both the executable and the application window.

## 📸 Screenshots (Optional)

_Once your application is built, consider adding a screenshot here to give users a visual idea of what it looks like._
_Example:_
![Application Screenshot](screenshots/app_screenshot.png)

## 📦 Prerequisites

Before you begin, ensure you have the following installed on your system:

* **Python 3.8 or higher:**
    * Download from: [python.org](https://www.python.org/downloads/)
    * Make sure to check "Add Python to PATH" during installation.
* **pip:** Python's package installer (usually comes with Python).

## 🚀 Installation

Follow these steps to get the project up and running on your local machine.

1.  **Clone the repository (or download the code):**
    ```bash
    git clone [https://github.com/your-username/video-downloader.git](https://github.com/your-username/video-downloader.git)
    # Or download the ZIP from GitHub and extract it
    ```

2.  **Navigate into the project directory:**
    ```bash
    cd video-downloader
    ```

3.  **Create a Virtual Environment (Recommended):**
    A virtual environment isolates your project's dependencies from other Python projects.
    ```bash
    python -m venv .venv
    ```

4.  **Activate the Virtual Environment:**
    * **Windows:**
        ```bash
        .venv\Scripts\activate
        ```
    * **macOS / Linux:**
        ```bash
        source .venv/bin/activate
        ```
    (You'll see `(.venv)` prepended to your command prompt, indicating the virtual environment is active.)

5.  **Install Project Dependencies:**
    This command will install all required libraries listed in `requirements.txt`.
    ```bash
    pip install -r requirements.txt
    ```

## 🛠️ Usage

### Running the Application Locally (for development/testing)

1.  **Activate your virtual environment** (if not already active, see step 4 in Installation).
2.  **Run the Flask application:**
    ```bash
    python app.py
    ```
3.  The application window should appear, and you can interact with it. You can close the console window that appears (if you opened it separately), but the application window needs the Python process running in the background.

### Building a Standalone Executable (for distribution)

You can package your application into a single executable file using PyInstaller, so others can run it without installing Python or dependencies.

1.  **Prepare your icon file:**
    * Ensure you have your desired application icon saved as an `.ico` file (e.g., `app_icon.ico`).
    * Place this `app_icon.ico` file in the **root directory** of your project (where `app.py` is located).

2.  **Clean previous PyInstaller builds (CRUCIAL!):**
    It's vital to clear old build artifacts to ensure new changes (like the icon or executable name) are applied.
    * Delete the `build` folder.
    * Delete the `dist` folder.
    * Delete the `VideoDownloader.spec` file (if it exists).

3.  **Run the PyInstaller command:**
    (Ensure your virtual environment is active)
    ```bash
    pyinstaller --noconsole --onefile --add-data "static;static" --add-data "app_icon.ico;." --collect-all flask_ui --icon "app_icon.ico" --name "VideoDownloader" app.py
    ```
    * `--noconsole`: Prevents a console window from appearing when the app runs.
    * `--onefile`: Packages everything into a single executable file.
    * `--add-data "static;static"`: Includes your `static` folder (CSS, JS) in the bundled app.
    * `--add-data "app_icon.ico;."`: Includes your icon file in the bundled app's temporary directory.
    * `--collect-all flask_ui`: Ensures all necessary parts of the `FlaskUI` library are included.
    * `--icon "app_icon.ico"`: Sets `app_icon.ico` as the icon for the generated `.exe` file.
    * `--name "VideoDownloader"`: Sets the name of the output executable to `VideoDownloader.exe`.

4.  **Find your executable:**
    After the process completes, your `VideoDownloader.exe` (or whatever name you chose) will be located in the `dist/` directory. You can now run this file directly.

## 📁 Project Structure

video-downloader/
├── .venv/                   # Python virtual environment
├── app.py                   # Main Flask application logic
├── requirements.txt         # List of Python dependencies
├── index.html               # Main UI page
├── static/                  # Contains CSS and JS for the frontend
│   ├── style.css
│   └── script.js
├── downloads/               # Directory for temporary video files (cleaned up)
├── app_icon.ico             # Your application icon file
├── build/                   # PyInstaller temporary build files (ignored by Git)
└── dist/                    # Output directory for the executable (ignored by Git)
└── VideoDownloader.spec     # PyInstaller build specification file (ignored by Git)


## ⚠️ Troubleshooting

* **`ImportError: cannot import name 'FlaskWebGui' from 'flaskwebgui'`:**
    This specific error means there's an issue with how `flaskwebgui` is installed or structured on your system. This project uses `FlaskUI` instead, which is more reliable. Ensure you have `FlaskUI` installed (`pip install FlaskUI`) and `from flask_ui import FlaskUI` in `app.py`.
* **Application starts but no window appears (when running executable):**
    * **Check for `app.run()`:** Make sure you are calling `ui.run()` and **NOT** `app.run()` inside the `if __name__ == '__main__':` block in `app.py`. `FlaskUI` handles starting the Flask server internally.
    * **Temporarily remove `--noconsole`:** Rebuild the executable without the `--noconsole` flag to see if any error messages appear in the console window when the app starts. This often reveals hidden issues (e.g., browser not found).
    * **Specify `browser_path`:** If no errors show, try explicitly setting the `browser_path` in `FlaskUI` constructor in `app.py` (e.g., `browser_path="C:/Program Files/Google/Chrome/Application/chrome.exe"`).
* **Download fails:**
    * Check your internet connection.
    * Ensure the tweet URL is publicly accessible and contains a video.
    * Check the console for `yt-dlp` errors (when running locally or without `--noconsole`).
    * Ensure `yt-dlp` is up-to-date (`pip install --upgrade yt-dlp`).

## 🔮 Recommendations for Further Enhancements

* **Error Reporting in UI:** Provide better visual feedback for download errors or invalid URLs directly in the application's user interface.
* **Download Progress:** Implement a way to show download progress within the UI.
* **Download Location Selection:** Allow users to choose their download directory instead of a fixed `downloads/` folder.
* **Notifications:** Add desktop notifications for download completion or failure.
* **Clipboard Monitoring (Optional Revisit):** As discussed, automate downloads by monitoring the clipboard for tweet URLs.
* **Video Playback:** Integrate a simple video player to preview downloaded content.

## 📄 License

This project is licensed under the MIT License - see the `LICENSE` file for details (you might need to create this file if you don't have one).
