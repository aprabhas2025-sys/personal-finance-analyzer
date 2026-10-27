# Finance Analyzer UI

A standalone React + TypeScript + Tailwind interface for the Finance Analyzer. The existing Python/Streamlit app remains unchanged.

## Run locally (Windows CMD)

```cmd
cd /d "C:\Users\prabhas\Downloads\mini project\finance-analyzer\finance-ui"
npm install
npm run dev
```

Open the local address Vite prints (normally `http://localhost:5174`). The starter CSV is synthetic. Uploaded CSV files are parsed in the browser and saved to this browser's local storage. This UI is not connected to the Streamlit account database or its ML categorizer.
