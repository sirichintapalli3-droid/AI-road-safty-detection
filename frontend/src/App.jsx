import { useEffect, useRef, useState } from "react";
import { assessAccidentImage, detectImage, getHealth, trackVideo } from "./services/api";
import { useAlerts } from "./hooks/useAlerts";
import "./styles.css";

const navigation = ["Overview", "Live monitor", "Analysis", "Violations", "Accidents", "Vehicles"];
const dangerTypes = ["ACCIDENT_SUSPECTED", "NO_HELMET", "OVERSPEEDING", "WRONG_WAY"];

function App() {
  const [health, setHealth] = useState(null);
  const [error, setError] = useState("");
  const [activeView, setActiveView] = useState("Overview");
  const [analysisMode, setAnalysisMode] = useState("vehicles");
  const [selectedFile, setSelectedFile] = useState(null);
  const [result, setResult] = useState(null);
  const [analysisError, setAnalysisError] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [cameraActive, setCameraActive] = useState(false);
  const [cameraError, setCameraError] = useState("");
  const videoRef = useRef(null);
  const cameraStreamRef = useRef(null);
  const { connected, alerts } = useAlerts();

  useEffect(() => { getHealth().then(setHealth).catch((reason) => setError(reason.message)); }, []);
  useEffect(() => () => stopCamera(), []);
  useEffect(() => {
    if (cameraActive && videoRef.current && cameraStreamRef.current) {
      videoRef.current.srcObject = cameraStreamRef.current;
    }
  }, [cameraActive]);

  async function runAnalysis() {
    if (!selectedFile) return;
    setAnalyzing(true); setAnalysisError("");
    try {
      const response = analysisMode === "video" ? await trackVideo(selectedFile) : analysisMode === "accident" ? await assessAccidentImage(selectedFile) : await detectImage(selectedFile);
      setResult(response);
    } catch (reason) { setAnalysisError(reason.message); }
    finally { setAnalyzing(false); }
  }

  async function startCamera() {
    setCameraError("");
    if (!navigator.mediaDevices?.getUserMedia) { setCameraError("Camera access is unavailable in this browser."); return; }
    try {
      cameraStreamRef.current = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      setCameraActive(true);
    } catch (reason) {
      const messages = {
        NotAllowedError: "Camera permission was blocked. Allow camera access for localhost and try again.",
        NotFoundError: "No camera was found. Connect a camera and try again.",
        NotReadableError: "The camera is already being used by another application.",
        SecurityError: "Camera access requires a secure localhost page.",
      };
      setCameraError(messages[reason.name] || "Camera could not be started. Check browser camera settings.");
    }
  }

  function stopCamera() {
    cameraStreamRef.current?.getTracks().forEach((track) => track.stop()); cameraStreamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null; setCameraActive(false);
  }

  async function captureCameraFrame() {
    if (!videoRef.current || !cameraActive) return;
    const canvas = document.createElement("canvas"); canvas.width = videoRef.current.videoWidth; canvas.height = videoRef.current.videoHeight;
    canvas.getContext("2d").drawImage(videoRef.current, 0, 0);
    canvas.toBlob(async (blob) => {
      if (!blob) return; setAnalyzing(true); setAnalysisError("");
      try { const file = new File([blob], "camera-frame.jpg", { type: "image/jpeg" }); setResult(await (analysisMode === "accident" ? assessAccidentImage(file) : detectImage(file))); }
      catch (reason) { setAnalysisError(reason.message); } finally { setAnalyzing(false); }
    }, "image/jpeg", 0.9);
  }

  const alertCounts = alerts.reduce((counts, alert) => { counts[alert.alert_type] = (counts[alert.alert_type] || 0) + 1; return counts; }, {});
  const dangerAlerts = alerts.filter((alert) => dangerTypes.includes(alert.alert_type));
  const isVideo = analysisMode === "video";
  const isAccident = result?.possible_accident === true;
  const analysisState = result?.possible_accident === true || result?.possible_accidents?.length > 0 || (isVideo && ["HIGH", "VERY_HIGH"].includes(result?.density_level)) ? "danger" : isVideo && result?.density_level === "MEDIUM" ? "warning" : result ? "safe" : "pending";
  const dangerActive = result ? analysisState === "danger" : dangerAlerts.length > 0;
  const systemState = error ? "danger" : result ? analysisState : dangerAlerts.length > 0 ? "danger" : health && connected ? "safe" : "pending";

  function selectMode(mode) { setAnalysisMode(mode); setSelectedFile(null); setResult(null); setAnalysisError(""); if (mode === "video") stopCamera(); }

  return <main className={`app-shell ${systemState}`}>
    <aside className="sidebar"><div className="brand"><span className="mark">RS</span><span>ROAD<br /><b>WATCH</b></span></div><div className="side-label">WORKSPACE</div><nav>{navigation.map((item) => <button className={activeView === item ? "active" : ""} key={item} onClick={() => setActiveView(item)}><span className="nav-glyph">{item === "Overview" ? "+" : item === "Live monitor" ? "o" : item === "Analysis" ? "~" : item === "Violations" ? "!" : item === "Accidents" ? "x" : "#"}</span>{item}</button>)}</nav><div className="sidebar-foot"><span className={`dot ${connected ? "online" : ""}`} />{connected ? "Alert stream live" : "Alert stream offline"}<small>PHASE 10</small></div></aside>
    <section className="workspace"><header className="workspace-head"><div><p className="eyebrow">Operations / {activeView}</p><h1>{activeView}</h1></div><div className={`system-pill ${systemState}`}><span className={`dot ${systemState === "safe" ? "online" : ""}`} />{systemState === "safe" ? "All systems normal" : systemState === "danger" ? "Danger detected" : systemState === "warning" ? "Review recommended" : "System connecting"}</div></header>
      <section className="metric-grid"><article><span>VEHICLES TODAY</span><strong>{isVideo && result ? result.total_unique_vehicles : "--"}</strong><small>{isVideo ? "Unique tracked IDs" : "Awaiting video analysis"}</small></article><article><span>TRAFFIC DENSITY</span><strong>{isVideo && result ? result.density_level : "--"}</strong><small>{isVideo ? `${result?.peak_visible_vehicles || 0} peak visible` : "No active scene"}</small></article><article><span>VIOLATIONS</span><strong>{(alertCounts.NO_HELMET || 0) + (alertCounts.OVERSPEEDING || 0) + (alertCounts.WRONG_WAY || 0) || "--"}</strong><small>Current session</small></article><article className={`accent ${dangerActive ? "danger" : "safe"}`}><span>{dangerActive ? "SAFETY ALERTS" : "SYSTEM STATUS"}</span><strong>{dangerActive ? dangerAlerts.length + (result?.possible_accident && !dangerAlerts.some((alert) => alert.alert_type === "ACCIDENT_SUSPECTED") ? 1 : 0) : connected ? "OK" : "--"}</strong><small>{dangerActive ? "Review required" : connected ? "No active danger" : "Channel offline"}</small></article></section>
      <section className="content-grid"><article className="panel monitor-panel"><div className="panel-head"><div><span className="panel-kicker">VISION INPUT</span><h2>{isVideo ? "Analyze traffic video" : analysisMode === "accident" ? "Review accident image" : "Inspect a frame"}</h2></div><span className="model-chip">{isVideo ? "YOLO + BYTE TRACK" : "YOLO / COCO"}</span></div><div className="analysis-tabs"><button className={analysisMode === "vehicles" ? "selected" : ""} onClick={() => selectMode("vehicles")}>Objects</button><button className={analysisMode === "accident" ? "selected" : ""} onClick={() => selectMode("accident")}>Accident image</button><button className={isVideo ? "selected" : ""} onClick={() => selectMode("video")}>Video</button></div>{!isVideo && <div className="input-tabs"><button className={!cameraActive ? "selected" : ""} onClick={stopCamera}>Upload image</button><button className={cameraActive ? "selected" : ""} onClick={startCamera}>Camera</button></div>}{cameraActive ? <div className="camera-view"><video ref={videoRef} autoPlay playsInline /><span className="camera-live"><i /> LIVE PREVIEW</span></div> : <label className="dropzone"><input type="file" accept={isVideo ? "video/mp4,video/avi,video/quicktime,video/x-msvideo" : "image/jpeg,image/png,image/webp"} onChange={(event) => { setSelectedFile(event.target.files[0]); setResult(null); }} /><span className="upload-mark">+</span><b>{selectedFile ? selectedFile.name : isVideo ? "Choose a traffic video" : "Choose an image"}</b><small>{isVideo ? "MP4, AVI, or MOV / 200 MB max" : "JPEG, PNG, or WebP / 10 MB max"}</small></label>}{cameraActive ? <div className="camera-actions"><button className="run-button" disabled={analyzing} onClick={captureCameraFrame}>{analyzing ? "Analyzing frame..." : "Capture and assess"}</button><button className="stop-button" onClick={stopCamera}>Stop camera</button></div> : <button className="run-button" disabled={!selectedFile || analyzing} onClick={runAnalysis}>{analyzing ? "Analyzing..." : isVideo ? "Track and analyze video" : analysisMode === "accident" ? "Assess accident image" : "Run vehicle detection"}</button>}{(cameraError || analysisError) && <p className="error-text">{cameraError || analysisError}</p>}{result && <div className={`result-strip ${isAccident ? "danger-result" : ""}`}><strong>{isVideo ? result.total_unique_vehicles : analysisMode === "accident" ? isAccident ? "!" : "OK" : result.detections.length}</strong><span>{isVideo ? `${result.density_level} density` : analysisMode === "accident" ? result.assessment.replaceAll("_", " ") : "objects detected"}</span><small>{isVideo ? `${result.processed_frames} frames / ${result.tracker}` : analysisMode === "accident" ? result.reason : `${result.image_width} x ${result.image_height} px`}</small></div>}</article><article className="panel alerts-panel"><div className="panel-head"><div><span className="panel-kicker">REAL-TIME FEED</span><h2>Latest alerts</h2></div><span className="alert-count">{alerts.length}</span></div>{alerts.length ? <div className="alert-list">{alerts.slice(0, 6).map((alert, index) => <div className="alert-row" key={`${alert.timestamp}-${index}`}><span className="alert-bullet">!</span><div><b>{alert.alert_type.replaceAll("_", " ")}</b><p>{alert.message}</p></div><time>{new Date(alert.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</time></div>)}</div> : <div className="empty-state"><span>--</span><p>No alerts in this session</p><small>Safety events will appear here as analysis runs.</small></div>}</article></section>
      <footer><span>ROADWATCH / AI TRAFFIC INTELLIGENCE</span><span>{health ? `${health.service} v${health.version}` : "SYSTEM INITIALIZING"}</span></footer></section>
  </main>;
}

export default App;
