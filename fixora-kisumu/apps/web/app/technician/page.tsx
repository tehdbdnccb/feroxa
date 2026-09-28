"use client";

import { useEffect, useState } from "react";
import { Shell } from "../../components/Shell";
import { AuthCard } from "../../components/AuthCard";
import { api, upload } from "../../lib/api";

type Repair = { id: string; device_id: string; issue: string; service_mode: string; address: string; status: string; assigned_technician_id: string | null };
type Me = { id: string; full_name: string; role: string };
type Profile = { available: boolean; years_experience: number; bio: string; latitude: number | null; longitude: number | null; service_radius_km: number; network_approved: boolean; credentials: string[] };

export default function Technician() {
  const [user, setUser] = useState<Me | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [jobs, setJobs] = useState<Repair[]>([]);
  const [years, setYears] = useState(3);
  const [radius, setRadius] = useState(15);
  const [message, setMessage] = useState("");

  async function refresh() {
    const me = await api<Me>("/v1/me");
    setUser(me);
    const [p, r] = await Promise.all([api<Profile>("/v1/technicians/me").catch(() => null), api<Repair[]>("/v1/repair-requests")]);
    if (p) { setProfile(p); setYears(p.years_experience); setRadius(p.service_radius_km); }
    setJobs(r);
  }

  useEffect(() => { api<Me>("/v1/me").then(() => refresh()).catch(() => setUser(null)); }, []);

  async function saveProfile() { try { const p = await api<Profile>("/v1/technicians/me", { method: "PATCH", body: JSON.stringify({ years_experience: years, service_radius_km: radius }) }); setProfile(p); setMessage("Profile saved."); } catch (error) { setMessage(error instanceof Error ? error.message : "Could not save profile"); } }
  async function toggle() {
    try {
      if (!profile?.available && (profile?.latitude === null || profile?.longitude === null)) {
        if (!navigator.geolocation) throw new Error("Location is unavailable in this browser.");
        const position = await new Promise<GeolocationPosition>((resolve, reject) => navigator.geolocation.getCurrentPosition(resolve, reject, { enableHighAccuracy: true, timeout: 10000 }));
        const p = await api<Profile>("/v1/technicians/me", { method: "PATCH", body: JSON.stringify({ latitude: position.coords.latitude, longitude: position.coords.longitude, available: true }) });
        setProfile(p);
      } else {
        const p = await api<Profile>("/v1/technicians/me", { method: "PATCH", body: JSON.stringify({ available: !profile?.available }) });
        setProfile(p);
      }
      await refresh();
    } catch (error) { setMessage(error instanceof Error ? error.message : "Could not change availability"); }
  }

  async function claim(id: string) { try { await api(`/v1/repair-requests/${id}/claim`, { method: "POST" }); await refresh(); } catch (error) { setMessage(error instanceof Error ? error.message : "Could not claim repair"); } }
  async function quote(id: string) { const rawParts = window.prompt("Parts amount (KSh)", "5000"); const rawLabour = window.prompt("Labour amount (KSh)", "1500"); if (rawParts === null || rawLabour === null) return; try { await api(`/v1/repair-requests/${id}/quotes`, { method: "POST", body: JSON.stringify({ parts_amount: Number(rawParts), labour_amount: Number(rawLabour), callout_amount: 0, warranty_days: 90, part_tier: "compatible" }) }); await refresh(); } catch (error) { setMessage(error instanceof Error ? error.message : "Could not send quote"); } }
  async function move(id: string, next: string) { try { await api(`/v1/repair-requests/${id}/status`, { method: "PATCH", body: JSON.stringify({ status: next }) }); await refresh(); } catch (error) { setMessage(error instanceof Error ? error.message : "Status update failed"); } }
  async function inspect(id: string) { try { await api(`/v1/repair-requests/${id}/inspections`, { method: "POST", body: JSON.stringify({ screen_ok: true, camera_ok: true, face_id_ok: true, speaker_ok: true, microphone_ok: true, charging_ok: true, notes: "Recorded through Fixora field checklist." }) }); await refresh(); } catch (error) { setMessage(error instanceof Error ? error.message : "Inspection failed"); } }
  async function evidence(id: string, stage: "pre" | "post") { const input = document.createElement("input"); input.type = "file"; input.accept = "image/jpeg,image/png,image/webp,application/pdf"; input.onchange = async () => { const file = input.files?.[0]; if (!file) return; try { const form = new FormData(); form.append("file", file); await upload(`/v1/repair-requests/${id}/evidence?stage=${stage}&kind=${stage === "pre" ? "device_condition" : "completion"}`, form); setMessage(`${stage} evidence uploaded.`); } catch (error) { setMessage(error instanceof Error ? error.message : "Evidence upload failed"); } }; input.click(); }

  if (!user) return <Shell><section className="narrow"><div className="eyebrow">Join the network</div><h1>Get repair jobs in Kisumu.</h1><p className="muted">Create a technician account. Network approval is handled separately in the trust center.</p><AuthCard role="technician" onAuthed={(result) => { setUser(result.user); refresh().catch(() => undefined); }} /></section></Shell>;

  return <Shell><section className="narrow-wide"><div className="page-heading"><div><div className="eyebrow">Technician workspace</div><h1>Run the repair, not the paperwork.</h1><p className="muted">Claims, quotes, inspections, evidence and payout status live in one workflow.</p></div><button className={`button ${profile?.available ? "primary" : "secondary"}`} onClick={toggle}>{profile?.available ? "Go offline" : "Go online"}</button></div>
    <div className="grid2 section"><div className="card"><div className="section-label">Profile</div><div className="mini-grid"><label className="label">Years experience<input className="input" type="number" value={years} onChange={(event) => setYears(Number(event.target.value))} /></label><label className="label">Service radius km<input className="input" type="number" value={radius} onChange={(event) => setRadius(Number(event.target.value))} /></label></div><p className="muted">Approved: {profile?.network_approved ? "yes" : "pending"} · Credentials: {profile?.credentials?.join(", ") || "none"}</p><button className="button secondary" onClick={saveProfile}>Save profile</button><button className="link-button left" onClick={() => toggle()}>Use current location & go online</button></div><div className="card dark-card"><div className="eyebrow light">Trust status</div><h3>{profile?.network_approved ? "Network approved" : "Awaiting verification"}</h3><p>Go online only after identity and business credentials are verified.</p></div></div>
    {message && <div className="notice section">{message}</div>}
    <div className="section-label section">Repair queue</div>
    {jobs.length === 0 ? <div className="card empty">No matching jobs right now.</div> : jobs.map((job) => <article className="card repair-card" key={job.id}><div className="repair-head"><div><span className="eyebrow">{job.service_mode}</span><h3>{job.issue}</h3><div className="muted">{job.address}</div></div><span className="status">{job.status.replaceAll("_", " ")}</span></div><div className="cta compact">{job.status === "requested" && !job.assigned_technician_id && <button className="button primary" onClick={() => claim(job.id)}>Claim job</button>}{job.status === "assigned" && <button className="button primary" onClick={() => quote(job.id)}>Send quote</button>}{job.status === "accepted" && <button className="button secondary" onClick={() => move(job.id, "en_route")}>En route</button>}{job.status === "en_route" && <button className="button secondary" onClick={() => move(job.id, "arrived")}>Arrived</button>}{job.status === "arrived" && <><button className="button secondary" onClick={() => inspect(job.id)}>Pre-inspection</button><button className="button secondary" onClick={() => evidence(job.id, "pre")}>Add evidence</button></>}{job.status === "inspecting" && <button className="button secondary" onClick={() => move(job.id, "in_repair")}>Start repair</button>}{job.status === "in_repair" && <><button className="button secondary" onClick={() => inspect(job.id)}>Post-inspection</button><button className="button secondary" onClick={() => evidence(job.id, "post")}>Add completion evidence</button></>}</div></article>)}
  </section></Shell>;
}
