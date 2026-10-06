const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

export async function getHealth() {
  const response = await fetch(`${API_URL}/health`);
  if (!response.ok) throw new Error("Backend health check failed");
  return response.json();
}

export async function detectImage(file) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API_URL}/detection/image`, { method: "POST", body: formData });
  if (!response.ok) throw new Error((await response.json()).detail || "Image detection failed");
  return response.json();
}

export async function assessAccidentImage(file) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API_URL}/detection/accident-image`, { method: "POST", body: formData });
  if (!response.ok) throw new Error((await response.json()).detail || "Accident assessment failed");
  return response.json();
}

export async function trackVideo(file) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API_URL}/detection/video/track`, { method: "POST", body: formData });
  if (!response.ok) throw new Error((await response.json()).detail || "Video analysis failed");
  return response.json();
}
