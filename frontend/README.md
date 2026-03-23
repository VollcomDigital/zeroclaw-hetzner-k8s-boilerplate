# Frontend mount point

`openwork/` is bind-mounted into the local `openwork` Compose service and served with `python -m http.server` for development.

Ships a minimal `index.html` so `/` is not a directory listing. Replace this directory’s contents with your OpenWork app (static build or your own dev workflow).
