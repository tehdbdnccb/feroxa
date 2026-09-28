"use client";

import { useEffect, useMemo, useState } from "react";
import { Shell } from "../../components/Shell";
import { AuthCard } from "../../components/AuthCard";
import { api } from "../../lib/api";

const issues = ["Cracked screen", "Battery", "Won't charge", "Camera", "Speaker / microphone", "Water / liquid damage", "Won't turn on", "Software / diagnostics"];
const modes = [
  ["mobile", "Come to me", "Best for common repairs."],
  ["pickup", "Pickup & repair", "For deeper diagnostics."],
  ["workshop", "Workshop", "For complex or specialist work."],
] as const;

type Device = { id: string; model: string; serial_last4: string | null; imei_last4: string | null };
type User = { id: string; full_name: string; role: string };

type Match = { technician_id: string; name: string; years_experience: number; average_rating: number; completed_jobs: number; background_verified: boolean; credentials: string[]; distance_km: number | null };

export default function Book() {
  const [user, setUser] = useState<User | null>(null);
  const [devices, setDevices] = useState<Device[]>([]);
  const [deviceId, setDeviceId] = useState("");
  const [model, setModel] = useState("iPhone 15 Pro");
  const [issue, setIssue] = useState(issues[0]);
  const [mode, setMode] = useState<(typeof modes)[number][0]>("mobile");
  const [address, setAddress] = useState("");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [matches, setMatches] = useState<Match[]>([]);

  useEffect(() => { api<User>("/v1/me").then(setUser).catch(() => setUser(null)); }, []);
  useEffect(() => { if (user) api<Device[]>("/v1/devices").then((items) => { setDevices(items); if (items[0]) { setDeviceId(items[0].id); setModel(items[0].model); } }).catch(() => undefined); }, [user]);

  const ready = useMemo(() => Boolean(user && model.trim() && issue && address.trim()), [user, model, issue, address]);

  function locate() {
    if (!navigator.geolocation) { setMessage("Location is not available in this browser. Enter your Kisumu location instead."); return; }
    navigator.geolocation.getCurrentPosition((position) => {
      setAddress("Current location in Kisumu");
      setMessage(`Location captured (${position.coords.latitude.toFixed(4)}, ${position.coords.longitude.toFixed(4)}).`);
      sessionStorage.setItem("fixora_lat", String(position.coords.latitude));
      sessionStorage.setItem("fixora_lon", String(position.coords.longitude));
    }, () => setMessage("Location permission was unavailable. Enter your location manually."));
  }

  async function createDevice() {
    const created = await api<Device>("/v1/devices", { method: "POST", body: JSON.stringify({ model }) });
    setDevices((current) => [created, ...current]);
    setDeviceId(created.id);
  }

  async function submit() {
    if (!ready) return;
    setBusy(true); setMessage(""); setMatches([]);
    try {
      let currentDeviceId = deviceId;
      if (!currentDeviceId) {
        const device = await api<Device>("/v1/devices", { method: "POST", body: JSON.stringify({ model }) });
        currentDeviceId = device.id;
      }
      const lat = sessionStorage.getItem("fixora_lat");
      const lon = sessionStorage.getItem("fixora_lon");
      const repair = await api<{ id: string }>("/v1/repair-requests", { method: "POST", body: JSON.stringify({ device_id: currentDeviceId, issue, notes, service_mode: mode, address, latitude: lat ? Number(lat) : null, longitude: lon ? Number(lon) : null }) });
      const found = await api<Match[]>(`/v1/repair-requests/${repair.id}/matches`);
      setMatches(found);
      setMessage(found.length ? "Your request is live. A verified technician can now claim it." : "Your request is live. We will surface a verified technician as soon as one is available.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not create repair request");
    } finally { setBusy(false); }
  }

  if (!user) return <Shell><section className="narrow"><div className="eyebrow">Book a repair</div><h1>Start with trust.</h1><p className="muted">Create an account so your device, quotes and Repair Passport stay under your control.</p><AuthCard role="customer" onAuthed={(result) => setUser(result.user)} /></section></Shell>;

  return (
    <Shell>
      <section className="narrow">
        <div className="eyebrow">Book a repair</div>
        <h1>Tell us what happened.</h1>
        <p className="muted">Your request becomes a structured repair job. No technician starts paid work without your approval.</p>

        <div className="card form-card">
          <div className="section-label">1 · Device</div>
          {devices.length ? <select className="select" value={deviceId} onChange={(event) => { setDeviceId(event.target.value); const found = devices.find((device) => device.id === event.target.value); if (found) setModel(found.model); }}><option value="">Choose a saved device</option>{devices.map((device) => <option key={device.id} value={device.id}>{device.model} · ••••{device.imei_last4 ?? ""}</option>)}</select> : null}
          <div className="field"><label className="label">Model<input className="input" value={model} onChange={(event) => setModel(event.target.value)} /></label></div>
          <button className="link-button left" onClick={createDevice}>Save this device to my account</button>

          <div className="section-label">2 · Problem</div>
          <div className="choice-grid">{issues.map((item) => <button key={item} className={`choice ${issue === item ? "selected" : ""}`} onClick={() => setIssue(item)}>{item}</button>)}</div>
          <div className="field"><label className="label">Anything else? (optional)<textarea className="textarea" rows={3} value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Describe symptoms, recent drops or liquid exposure." /></label></div>

          <div className="section-label">3 · Service</div>
          <div className="choice-grid">{modes.map(([value, title, body]) => <button key={value} className={`mode-card ${mode === value ? "selected" : ""}`} onClick={() => setMode(value)}><b>{title}</b><span>{body}</span></button>)}</div>
          <div className="field"><label className="label">Kisumu location<input className="input" value={address} onChange={(event) => setAddress(event.target.value)} placeholder="e.g. Milimani, Mega City or Kisumu CBD" /></label><button className="link-button left" onClick={locate}>Use my current location</button></div>
          {message && <div className="notice">{message}</div>}
          <button className="button primary full" disabled={!ready || busy} onClick={submit}>{busy ? "Creating repair request…" : "Find a verified technician"}</button>
        </div>

        {matches.length > 0 && <div className="section"><div className="section-label">Available network</div>{matches.map((match) => <div className="card tech-card" key={match.technician_id}><div><b>{match.name}</b><div className="muted">{match.years_experience} years · {match.completed_jobs} repairs · {match.average_rating.toFixed(1)}★</div><div className="credential-row">{match.background_verified && <span className="pill">Background verified</span>}{match.credentials.map((credential) => <span className="pill" key={credential}>{credential.replaceAll("_", " ")}</span>)}{match.distance_km !== null && <span className="pill">{match.distance_km} km</span>}</div></div></div>)}</div>}
      </section>
    </Shell>
  );
}
