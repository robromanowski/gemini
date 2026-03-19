# Add your Connect server (one-time setup)
```
rsconnect add \
  --server https://your-connect-server.company.com \
  --name myserver \
  --api-key YOUR_API_KEY
```

# Deploy — run from the project folder
```
rsconnect deploy streamlit \
  --name myserver \
  --entrypoint streamlit_app.py \
  --title "Trout Stream Data Explorer" \
  . 
```

>The . at the end deploys the whole directory, so streamlit_app.py, requirements.txt, and the data/ folder all go up together.

After first deploy, redeployments are even simpler — rsconnect saves the app ID in a manifest:

```
rsconnect redeploy streamlit .
```
