"use client";

import { useEffect, useState } from "react";
import { Shell } from "../../components/Shell";
import { AuthCard } from "../../components/AuthCard";
import { api } from "../../lib/api";

type Repair = { id: string; device_id: string; issue: string; service_mode: string; address: string; status: string; assigned_technician_id: string | null; created_at: string };
type Quote = { id: string; technician_id: string; parts_amount: number; labour_amount: number; callout_amount: number; warranty_days: number; part_tier: string; customer_accepted: boolean; total_amount: number };
type Notification = { id: string; kind: string; title: string; body: string; read_at: string | null; created_at: string; };
type User = { id: string; full_name: string; role: string };

const currency = (value: number) => `KSh ${value.toLocaleString()}`;

export default function Dashboard() {
  const [user, setUser] = useState<User | null>(null);
  const [repairs, setRepairs] = useState<Repair[]>([]);
  const [quotes, setQuotes] = useState<Record<string, Quote[]>>({});
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [message, setMessage] = useState("");
  const [paymentPhone, setPaymentPhone] = useState("+2547");
  const [paymentState, setPaymentState] = useState<Record<string, string>>({});

  async function load() {
    const items = await api<Repair[]>("/v1/repair-requests");
    setRepairs(items);
    const entries = await Promise.all(items.map(async (repair) => [repair.id, await api<Quote[]>(`/v1/repair-requests/${repair.id}/quotes`)] as const));
    setQuotes(Object.fromEntries(entries));
    setNotifications(await api<Notification[]>("/v1/notifications"));
    const paymentEntries = await Promise.all(items.filter((repair) => repair.status === "awaiting_payment").map(async (repair) => [repair.id, (await api<{ status: string }>(`/v1/repair-requests/${repair.id}/payment`)).status] as const));
    setPaymentState(Object.fromEntries(paymentEntries));
  }

  useEffect(() => { api<User>("/v1/me").then((me) => { setUser(me); load().catch(() => undefined); }).catch(() => setUser(null)); }, []);

  async function acceptQuote(id: string) { try { await api(`/v1/quotes/${id}/accept`, { method: "POST" }); await load(); setMessage("Quote accepted. Your technician can now begin the repair workflow."); } catch (error) { setMessage(error instanceof Error ? error.message : "Could not accept quote"); } }
  async function pay(repairId: string) { try { await api(`/v1/repair-requests/${repairId}/payments/mpesa`, { method: "POST", body: JSON.stringify({ phone: paymentPhone }) }); setMessage("M-Pesa prompt requested. Complete the prompt on your phone."); await load(); } catch (error) { setMessage(error instanceof Error ? error.message : "Could not start payment"); } }
  async function confirm(repairId: string) { try { await api(`/v1/repair-requests/${repairId}/status`, { method: "PATCH", body: JSON.stringify({ status: "completed" }) }); await load(); setMessage("Handover confirmed. The repair is now part of the device passport."); } catch (error) { setMessage(error instanceof Error ? error.message : "Could not confirm handover"); } }

  if (!user) return <Shell><section className="narrow"><div className="eyebrow">My repairs</div><h1>Your repair timeline.</h1><p className="muted">Sign in to see quotes, payment status, notifications and your device history.</p><AuthCard role="customer" onAuthed={(result) => { setUser(result.user); load().catch(() => undefined); }} /></section></Shell>;

  return <Shell><section className="narrow-wide"><div className="page-heading"><div><div className="eyebrow">Customer dashboard</div><h1>Hi, {user.full_name.split(" ")[0]}.</h1><p className="muted">Your device is tracked from request to handover.</p></div><button className="button secondary" onClick={() => load()}>Refresh</button></div>
    {notifications.length > 0 && <div className="notification-strip">{notifications[0].title}<span>{notifications[0].body}</span></div>}
    {message && <div className="notice section">{message}</div>}
    {repairs.length === 0 ? <div className="card empty"><h3>No repair yet.</h3><p className="muted">Start with a device and a problem. We'll turn it into a structured job.</p></div> : repairs.map((repair) => <article className="card repair-card" key={repair.id}><div className="repair-head"><div><span className="eyebrow">{repair.service_mode}</span><h3>{repair.issue}</h3><div className="muted">{repair.address}</div></div><span className="status">{repair.status.replaceAll("_", " ")}</span></div>
      {(quotes[repair.id] ?? []).map((quote) => <div className={`quote ${quote.customer_accepted ? "accepted" : ""}`} key={quote.id}><div><b>{currency(quote.total_amount)}</b><div className="muted">{quote.part_tier} parts · {quote.warranty_days}-day warranty</div></div>{!quote.customer_accepted && repair.status === "quoted" && <button className="button primary" onClick={() => acceptQuote(quote.id)}>Accept quote</button>}{quote.customer_accepted && repair.status === "awaiting_payment" && <><input className="input small-input" value={paymentPhone} onChange={(event) => setPaymentPhone(event.target.value)} /><button className="button primary" onClick={() => pay(repair.id)}>Pay by M-Pesa</button></>}{quote.customer_accepted && repair.status === "awaiting_payment" && <button className="button secondary" disabled={paymentState[repair.id] !== "success"} onClick={() => confirm(repair.id)}>{paymentState[repair.id] === "success" ? "Confirm handover" : "Waiting for payment"}</button>}</div>)}</article>)}
  </section></Shell>;
}
