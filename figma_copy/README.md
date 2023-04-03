This is a "Get a Copy" Automation using Selenium.

Since the Figma API Does not allow to fetch files direcly from Community, we have to copy to our Drafts, get access, then fetch via API.

This script allows to automate the Copy process.

## Usage

Create `.env`, set the Figma credentials for authentication.
If you are using Figma with Google, you acn use Reset password to create a password for your Figma Account.

```txt
# .env
FIGMA_EMAIL=<your-email>
FIGMA_PASSWORD=<your-password>
```

Then run

```bash
python3 main.py --file='../data/latest/index.json' --batch-size=500
```
