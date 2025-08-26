# Record a short CLI GIF on Windows

Option A — Snipping Tool (Windows 11)
1) Open Snipping Tool → New → Record (camcorder icon)
2) Select the terminal area showing your project
3) Run the demo command in the terminal:
   
   PowerShell
   python -m src.app.cli "What is RAG and why use it?" --k 3 --provider offline
   
4) Stop recording and save as MP4
5) Convert to GIF with ShareX (right-click) or an online converter
6) Save the GIF to assets/cli_demo.gif and commit

Option B — ScreenToGif (portable)
1) Download ScreenToGif → Recorder → drag to terminal area
2) Record 15–30 seconds while running the demo command
3) Trim and save to assets/cli_demo.gif

Tip
- Keep the terminal font size larger so text is readable
- Keep it short; just one question is enough
