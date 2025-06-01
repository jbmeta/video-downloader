# VideoDownloader

A simple, standalone desktop application built with Flask and FlaskUI for downloading videos from Twitter/X.

## ✨ Features

* Download videos from valid Twitter/X tweet URLs.
* Choose from available video resolutions.
* Automatically cleans up temporary download files after use.
* Packaged as a single executable for easy distribution on Windows.

## 🚀 Getting Started

Follow these instructions to get a copy of the project up and running on your local machine for development and testing purposes, or to create an executable.

### Prerequisites

Before you begin, ensure you have the following installed:

* **Python 3.8 or higher:**
    * Download from: [python.org](https://www.python.org/downloads/)
    * It's recommended to add Python to your system's PATH during installation.

### Installation

1.  **Clone the Repository (or Download the Code):**
    If you're using Git:
    ```bash
    git clone [https://github.com/jbmeta/VideoDownloader.git](https://github.com/jbmeta/VideoDownloader.git)
    cd VideoDownloader
    ```
    If you downloaded a ZIP file, extract it and navigate into the project directory.

2.  **Create a Virtual Environment (Recommended):**
    It's good practice to create a virtual environment to manage dependencies for your project.
    ```bash
    python -m venv .venv
    ```

3.  **Activate the Virtual Environment:**
    * **On Windows:**
        ```bash
        .venv\Scripts\activate
        ```
    * **On macOS/Linux:**
        ```bash
        source .venv/bin/activate
        ```
    (You'll see `(.venv)` appear in your terminal prompt, indicating the virtual environment is active.)

4.  **Install Dependencies:**
    First, create a `requirements.txt` file in your project's root directory with the following content:

    ```
    Flask
    FlaskUI
    yt-dlp
    ```

    Then, install them using pip:
    ```bash
    pip install -r requirements.txt
    ```

### ▶️ Usage (Local Execution)

To run the application locally without creating an executable:

1.  **Activate your virtual environment** (if not already active, see "Installation" step 3).
2.  **Run the Flask application:**
    ```bash
    python app.py
    ```
3.  A desktop window titled "Twitter/X Video Downloader" should open, displaying the application's interface.
4.  Enter a valid Twitter/X tweet URL (e.g., `https://x.com/user/status/1234567890`) into the text box, click "Get Info," choose a resolution, and click "Download."

### 📦 Creating an Executable (for Windows)

You can package your application into a single executable file for easy distribution on Windows, using PyInstaller.

1.  **Install PyInstaller:**
    Make sure your virtual environment is active, then install PyInstaller:
    ```bash
    pip install pyinstaller
    ```

2.  **Prepare Your Application Icon:**
    * Obtain an icon file in **`.ico` format** (e.g., `app_icon.ico`).
    * Place this `app_icon.ico` file directly in the **root directory of your project**, next to `app.py`.

3.  **Clean Previous Builds (Crucial!):**
    Before packaging, always ensure you remove any old build artifacts to prevent issues:
    * Delete the `build` folder.
    * Delete the `dist` folder.
    * Delete the `VideoDownloader.spec` file (or `app.spec` if it existed from previous builds).

4.  **Run the PyInstaller Command:**
    Execute the following command in your project's root directory:
    ```bash
    pyinstaller --noconsole --onefile --add-data "static;static" --add-data "app_icon.ico;." --collect-all flask_ui --icon "app_icon.ico" --name "VideoDownloader" app.py
    ```
    * `--noconsole`: Prevents a black console window from appearing when the app runs.
    * `--onefile`: Packages everything into a single `.exe` file.
    * `--add-data "static;static"`: Includes your `static` folder (CSS, JS) in the build.
    * `--add-data "app_icon.ico;."`: Includes your icon file in the bundled application.
    * `--collect-all flask_ui`: Ensures all necessary components of `FlaskUI` are bundled.
    * `--icon "app_icon.ico"`: Sets the icon for the generated `VideoDownloader.exe` file.
    * `--name "VideoDownloader"`: Specifies the name of the output executable.

5.  **Find Your Executable:**
    Once PyInstaller completes, your executable will be located in the `dist/` folder, named `VideoDownloader.exe`.

## ⚠️ Troubleshooting

* **`ImportError: cannot import name 'FlaskWebGui' from 'flaskwebgui'`:**
    This specific error indicates a problem with the `flaskwebgui` library's import structure or installation. Ensure you have correctly `pip install FlaskUI` and that your `app.py` uses `from flask_ui import FlaskUI`.
* **Application starts but no window appears (from executable):**
    * **Check `app.run()` vs `ui.run()`:** Ensure you have *removed* any `app.run()` calls and are exclusively using `ui.run()` within your `if __name__ == '__main__':` block.
    * **Try without `--noconsole`:** Temporarily remove `--noconsole` from your PyInstaller command. If a console window appears with errors, that's your clue.
    * **Specify `browser_path`:** If no errors appear, `FlaskUI` might not be finding your browser. In `app.py`, try adding `browser_path="C:/Path/To/Your/Browser/chrome.exe"` to your `FlaskUI` constructor. Remember to use forward slashes for paths in Python.
* **"Video Not Found" or "Download Error":**
    * Ensure the Twitter/X URL is a direct link to a tweet, not a user profile or other page.
    * The video might be private, geo-restricted, or removed.
    * Your internet connection might be unstable.

## 💡 Suggestions for Future Enhancements

* **Download Progress Bar:** Implement real-time progress updates in the UI.
* **Download Queue:** Allow users to add multiple videos to a download queue.
* **Settings Page:** Add options for default download directory, preferred resolution, etc.
* **Error Reporting in UI:** Display more user-friendly error messages directly in the application's interface.
* **Cross-platform support:** Test and refine PyInstaller commands for macOS and Linux.

## 🤝 Contributing

If you'd like to contribute to this project, feel free to fork the repository, make your changes, and submit a pull request.