"use client";

import { useEffect, useState } from "react";
import { Shell } from "../../components/Shell";
import { api } from "../../lib/api";
import { AuthCard } from "../../components/AuthCard";

type User = { id: string; full_name: string; role: string };
type Tech = { id: string; name: string; email: string; available: boolean; network_approved: boolean; years_experience: number; background_verified: boolean; completed_jobs: number; average_rating: number; credentials: { id: string; kind: string; reference: string }[] };
type Payout = { id: string; amount: number; status: string; technician_id: string; repair_request_id: string; created_at: string };
type Dispute = { id: string; repair_request_id: string; reason: string; details: string; status: string; resolution: string };

export default function Admin() {
  const [user, setUser] = useState<User | null>(null);
  const [techs, setTechs] = useState<Tech[]>([]);
  const [payouts, setPayouts] = useState<Payout[]>([]);
  const [disputes, setDisputes] = useState<Dispute[]>([]);
  const [message, setMessage] = useState("");

  async function load() {
    const [technicians, payoutRows, disputeRows] = await Promise.all([api<Tech[]>("/v1/admin/technicians"), api<Payout[]>("/v1/admin/payouts"), api<Dispute[]>("/v1/admin/disputes")]);
    setTechs(technicians); setPayouts(payoutRows); setDisputes(disputeRows);
  }
  useEffect(() => { api<User>("/v1/me").then((me) => { if (me.role !== "admin") setUser(null); else { setUser(me); load().catch(() => undefined); } }).catch(() => setUser(null)); }, []);

  async function credential(tech: Tech, kind: string) { const reference = window.prompt(`Verification reference for ${kind}`, "MANUAL-REVIEW"); if (!reference) return; try { await api(`/v1/admin/technicians/${tech.id}/credentials`, { method: "POST", body: JSON.stringify({ kind, reference }) }); await load(); } catch (error) { setMessage(error instanceof Error ? error.message : "Credential action failed"); } }
  async function approval(tech: Tech, approved: boolean) { try { await api(`/v1/admin/technicians/${tech.id}/approval`, { method: "PATCH", body: JSON.stringify({ approved, background_verified: true, reason: approved ? "Pilot network approval" : "Removed from network" }) }); await load(); } catch (error) { setMessage(error instanceof Error ? error.message : "Approval action failed"); } }
  async function updatePayout(id: string, next: "paid" | "held") { try { await api(`/v1/admin/payouts/${id}`, { method: "PATCH", body: JSON.stringify({ status: next, notes: `Pilot payout marked ${next}.` }) }); await load(); } catch (error) { setMessage(error instanceof Error ? error.message : "Payout update failed"); } }
  async function resolveDispute(id: string, next: "resolved" | "rejected") { const resolution = window.prompt("Resolution", next === "resolved" ? "Issue reviewed and resolved by Fixora trust team." : "Dispute reviewed and rejected."); if (!resolution) return; try { await api(`/v1/admin/disputes/${id}`, { method: "PATCH", body: JSON.stringify({ status: next, resolution }) }); await load(); } catch (error) { setMessage(error instanceof Error ? error.message : "Dispute update failed"); } }

  if (!user) return <Shell><section className="narrow"><div className="eyebrow">Trust center</div><h1>Curate the network.</h1><p className="muted">Use the pre-provisioned admin account. Customer/technician accounts can never self-upgrade to admin.</p><AuthCard role="customer" onAuthed={(result) => { if (result.user.role === "admin") { setUser(result.user); load().catch(() => undefined); } else setMessage("This account is not an admin."); }} /></section></Shell>;

  return <Shell><section className="narrow-wide"><div className="page-heading"><div><div className="eyebrow">Trust center</div><h1>Approve the people behind the brand.</h1><p className="muted">Separate identity, business and Apple credential verification.</p></div><button className="button secondary" onClick={() => load()}>Refresh</button></div>{message && <div className="notice section">{message}</div>}
    <div className="section-label section">Technicians</div>{techs.map((tech) => <article className="card repair-card" key={tech.id}><div className="repair-head"><div><h3>{tech.name}</h3><div className="muted">{tech.email} · {tech.years_experience} years · {tech.completed_jobs} jobs · {tech.average_rating.toFixed(1)}★</div><div className="credential-row">{tech.credentials.length ? tech.credentials.map((credential) => <span className="pill" key={credential.id}>{credential.kind}</span>) : <span className="pill muted-pill">No credentials yet</span>}</div></div><span className="status">{tech.network_approved ? "approved" : "pending"}</span></div><div className="cta compact"><button className="button secondary" onClick={() => credential(tech, "identity")}>Verify identity</button><button className="button secondary" onClick={() => credential(tech, "business")}>Verify business</button><button className="button secondary" onClick={() => credential(tech, "apple_certified")}>Verify Apple credential</button>{tech.network_approved ? <button className="button danger" onClick={() => approval(tech, false)}>Suspend</button> : <button className="button primary" onClick={() => approval(tech, true)}>Approve network</button>}</div></article>)}
    <div className="section-label section">Dispute queue</div>{disputes.length === 0 ? <div className="card empty">No disputes in the trust queue.</div> : disputes.map((dispute) => <article className="card repair-card" key={dispute.id}><div><span className="status">{dispute.status}</span><h3>{dispute.reason}</h3><div className="muted">Repair {dispute.repair_request_id.slice(0, 8)}</div><p>{dispute.details}</p></div>{dispute.status === "open" && <div className="cta compact"><button className="button primary" onClick={() => resolveDispute(dispute.id, "resolved")}>Resolve</button><button className="button secondary" onClick={() => resolveDispute(dispute.id, "rejected")}>Reject</button></div>}</article>)}
    <div className="section-label section">Payout queue</div>{payouts.length === 0 ? <div className="card empty">No payout records yet.</div> : payouts.map((payout) => <article className="card quote" key={payout.id}><div><b>KSh {payout.amount.toLocaleString()}</b><div className="muted">Repair {payout.repair_request_id.slice(0, 8)} · {payout.status}</div></div>{payout.status === "pending" && <div className="cta compact"><button className="button secondary" onClick={() => updatePayout(payout.id, "held")}>Hold</button><button className="button primary" onClick={() => updatePayout(payout.id, "paid")}>Mark paid</button></div>}</article>)}
  </section></Shell>;
}
