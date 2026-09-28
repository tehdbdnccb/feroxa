"use client";

import { useState } from "react";
import { api } from "../lib/api";

type AuthResult = { access_token: string; user: { id: string; full_name: string; role: string } };

export function AuthCard({ role, onAuthed }: { role: "customer" | "technician"; onAuthed: (result: AuthResult) => void }) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("+2547");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function submit() {
    setBusy(true);
    setMessage("");
    try {
      const body = mode === "login" ? { email, password } : { email, full_name: name, phone, password, role };
      const result = await api<AuthResult>(`/v1/auth/${mode}`, { method: "POST", body: JSON.stringify(body) });
      onAuthed(result);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Authentication failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card glass form-card">
      <div className="eyebrow">{role === "technician" ? "Technician access" : "Customer access"}</div>
      <h2>{mode === "login" ? "Welcome back." : "Create your Fixora account."}</h2>
      {mode === "register" && (
        <div className="field"><label className="label">Full name<input className="input" value={name} onChange={(event) => setName(event.target.value)} /></label></div>
      )}
      {mode === "register" && (
        <div className="field"><label className="label">Mobile number<input className="input" value={phone} onChange={(event) => setPhone(event.target.value)} /></label></div>
      )}
      <div className="field"><label className="label">Email<input className="input" type="email" value={email} onChange={(event) => setEmail(event.target.value)} /></label></div>
      <div className="field"><label className="label">Password<input className="input" type="password" minLength={10} value={password} onChange={(event) => setPassword(event.target.value)} /></label></div>
      {message && <div className="error">{message}</div>}
      <button className="button primary full" disabled={busy} onClick={submit}>{busy ? "Working…" : mode === "login" ? "Sign in" : "Create account"}</button>
      <button className="link-button" onClick={() => setMode(mode === "login" ? "register" : "login")}>{mode === "login" ? "Create an account" : "I already have an account"}</button>
    </div>
  );
}
