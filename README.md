# How to use
- Go to releases tab and download the latest release.
- Place the .exe into an arbitrary folder on the fastest storage device you have (anything that doesn't has moving parts inside and is connected through USB 3.0 (if applicable). Basically - put it on an SSD)
- Run the .exe file and do what it says. If it spits shit like "Traceback (most recent call last)", please repot this as an error.
- If it asks "Allow python to access network" - click yes or something like that.
- If everything goes well you should end up on a webpage, which should be quite intuitive to navigate.
- Now look at the folder the .exe is in, there should be a file called "tag_match.py".
- Open it as a text file, preferably with Notepad++ (pls use Notepad++, don't do it in default Windows notepad).
- That file describes a query to filter posts by. It has instructions inside. Edit it to your liking (and don't forget to save).
- Go back to the webpage and click "Re-Download export", wait for it to finish.
- Then click "Execute Query", wait for it to finish.
- The results will be displayed below.
- GIF-like posts and videos are labeled as such with an icon in the top right corner.
- Click on an image/video to enlarge it and click again or press "Escape" to close the fullres overlay.

The amount of RAM used by the tool equals to roughly 90% of the size of the database
(as of 04-02-2024 it's almost 4GB and growing exponentially).
Although this is only true when actively performing queries.
If you perform a query, close the software and open it again -
the amount of RAM used will be the size of the cached query (usually a few hundred megabytes at most).
If you perform a query again - the RAM usage will go back to the numbers mentioned above.

You can only have one webpage with this tool opened.

For now it's only possible to search by tags.
If at least someone finds this tool useful - support for other query types
will be added.

# Other ways to run the tool
Alternatively, you can download the repository and run the tool directly.
Should work both on Linux and Windows.

For that you need:
- Python installed https://www.python.org/
- BeautifulSoup python package https://pypi.org/project/beautifulsoup4/
- Requests python package https://pypi.org/project/requests/

Once all the requirements are satisfied - run launcher.cmd, if you're on Windows.
Or simply execute main.py if .cmd file is not an option for you.

For now, when running the tool directly (through main.py) the port is hardcoded to 8089.

# Compiling to .exe yourself
Compiling to exe works out of the box, there are no any kind of special setups needed.

All you need is:
- (Obviously) Download the repository.
- Python installed https://www.python.org/
- PyInstaller python package https://pypi.org/project/pyinstaller/

Once all the requirements are satisfied - run compile_exe.cmd, if you're on Windows.
Or simply execute compile_exe.py if .cmd file is not an option for you.

# Feedback is very much welcome
