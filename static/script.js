document.addEventListener('DOMContentLoaded', () => {
    const tweetUrlInput = document.getElementById('tweetUrl');
    const getVideoBtn = document.getElementById('getVideoBtn');
    const loadingDiv = document.getElementById('loading');
    const errorMessageDiv = document.getElementById('errorMessage');
    const downloadOptionsDiv = document.getElementById('downloadOptions');
    const resolutionListDiv = document.getElementById('resolutionList');

    getVideoBtn.addEventListener('click', async () => {
        const tweetUrl = tweetUrlInput.value.trim();
        if (!tweetUrl) {
            displayMessage('Please enter a X URL.', 'error');
            return;
        }

        const xUrlPattern = /https?:\/\/(?:www\.)?x\.com\/\w+\/status\/\d+/;
        if (!xUrlPattern.test(tweetUrl)) {
            displayMessage('Invalid X URL format. Please use a link like "https://x.com/user/status/123456789".', 'error');
            return;
        }

        showLoading();
        clearMessages();
        hideDownloadOptions();

        try {
            const response = await fetch('/get_video_info', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ tweet_url: tweetUrl })
            });

            const data = await response.json();

            if (!response.ok) {
                displayMessage(data.error || 'Failed to get video information.', 'error');
                return;
            }

            if (data.formats && data.formats.length > 0) {
                displayDownloadOptions(data.formats);
            } else {
                displayMessage('No downloadable videos found for this tweet.', 'error');
            }

        } catch (error) {
            console.error('Error:', error);
            displayMessage('An error occurred while fetching video information. Please try again.', 'error');
        } finally {
            hideLoading();
        }
    });

    function showLoading() {
        loadingDiv.classList.remove('hidden');
    }

    function hideLoading() {
        loadingDiv.classList.add('hidden');
    }

    function clearMessages() {
        errorMessageDiv.classList.add('hidden');
        errorMessageDiv.textContent = '';
    }

    function displayMessage(message, type = 'info') {
        errorMessageDiv.textContent = message;
        errorMessageDiv.classList.remove('hidden');
        if (type === 'error') {
            errorMessageDiv.style.backgroundColor = '#f2dede';
            errorMessageDiv.style.borderColor = '#ebccd1';
            errorMessageDiv.style.color = '#d9534f';
        } else {
            errorMessageDiv.style.backgroundColor = '#dff0d8';
            errorMessageDiv.style.borderColor = '#d6e9c6';
            errorMessageDiv.style.color = '#3c763d';
        }
    }

    function hideDownloadOptions() {
        downloadOptionsDiv.classList.add('hidden');
        resolutionListDiv.innerHTML = '';
    }

    function displayDownloadOptions(formats) {
        resolutionListDiv.innerHTML = ''; // Clear previous options
        formats.forEach(format => {
            const item = document.createElement('div');
            item.classList.add('resolution-item');

            const info = document.createElement('span');
            const fileSizeMB = format.filesize ? (format.filesize / (1024 * 1024)).toFixed(2) : 'N/A';
            info.classList.add('resolution-info');
            // Make sure this line is exactly as below:
            info.textContent = `${format.resolution} (${fileSizeMB} MB)`;


            const downloadButton = document.createElement('button');
            downloadButton.textContent = 'Download';
            downloadButton.addEventListener('click', () => initiateDownload(format.url, format.resolution));

            item.appendChild(info);
            item.appendChild(downloadButton);
            resolutionListDiv.appendChild(item);
        });
        downloadOptionsDiv.classList.remove('hidden');
    }

    async function initiateDownload(videoUrl, resolution) {
        displayMessage(`Downloading ${resolution} video... This may take a moment.`, 'info');
        try {
            // For direct browser download, we'll open the URL in a new tab/window
            // The Flask backend will handle the actual streaming of the file
            window.open(videoUrl, '_blank');
            displayMessage('Download should start in a new tab/window. Check your browser downloads.', 'info');
        } catch (error) {
            console.error('Error initiating download:', error);
            displayMessage('Failed to initiate download. Please try again.', 'error');
        }
    }
});