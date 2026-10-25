"""Deployment mode. Render sets RENDER=true automatically; for any other host set FINANCE_HOSTED=1."""
import os


def is_hosted() -> bool:
    return bool(os.environ.get("RENDER") or os.environ.get("FINANCE_HOSTED", "").strip() not in ("", "0", "false", "False"))


LOCAL_CAPTION = ("Upload a bank/UPI statement CSV. Everything runs locally and your data never leaves this machine.")

HOSTED_CAPTION = ("Upload a bank/UPI statement CSV. **This is a hosted demo:** your file is processed on the server and kept in a "
                  "temporary file tied to this browser session. It is deleted when you press *Clear stored data* or when the server "
                  "cleans up old sessions (after 24 hours idle) or restarts. For a real statement, run the app locally instead "
                  "(see the README), or use the sample data.")

HOSTED_RETRAIN_NOTE = ("In this hosted demo, corrections apply to your session (and to the same merchant) but the model is not retrained, "
                       "so one visitor's corrections can never change what another visitor sees. Run locally to retrain the model.")
