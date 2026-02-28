const express = require("express");
const { spawn } = require("child_process");

const app = express();

app.get("/live", (req, res) => {
  res.writeHead(200, {
    "Content-Type": "multipart/x-mixed-replace; boundary=frame",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "Pragma": "no-cache"
  });

  const ffmpeg = spawn("ffmpeg", [
    "-rtsp_transport", "tcp",
    "-i", "rtsp://gooncam:gooncam123@10.121.8.125:554/stream1",
    "-vf", "scale=640:480",   // 🔥 resize for browser
    "-r", "15",               // reduce fps
    "-f", "mjpeg",
    "-"
  ]);

  ffmpeg.stdout.on("data", (data) => {
    res.write(`--frame\r\nContent-Type: image/jpeg\r\n\r\n`);
    res.write(data);
    res.write("\r\n");
  });

  ffmpeg.stderr.on("data", (data) => {
    console.log(data.toString());
  });

  req.on("close", () => {
    ffmpeg.kill("SIGINT");
  });
});

app.listen(8080, () => {
  console.log("Camera stream running at http://localhost:8080/live");
});