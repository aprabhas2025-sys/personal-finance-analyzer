# Finance Analyzer UI

React + TypeScript + Tailwind dashboard that the Streamlit app embeds after sign-in (`app/app.py` loads `finance-ui/dist`).

## Run locally

```bash
cd finance-ui
npm install
npm run dev     # Vite dev server
npm run build   # writes dist/, which app/app.py serves
```

Uploaded CSV files are parsed in the browser and kept in local storage. Commit the rebuilt `dist/` after changes: the hosted app has no Node build step.
