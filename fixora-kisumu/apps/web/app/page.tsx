import Link from "next/link";
import { Shell } from "../components/Shell";

const trustItems = [
  ["Verified network", "Identity, business and credentials are reviewed before a technician can go online."],
  ["Upfront quote", "Approve the price before repair work starts. Changes require a new customer approval."],
  ["Repair Passport", "Keep a durable record of inspections, work performed, warranty and evidence."],
];

export default function Home() {
  return (
    <Shell>
      <section className="hero hero-strong">
        <div className="hero-copy">
          <div className="eyebrow">Kisumu · iPhone-first</div>
          <h1>Repair your Apple device without the trust gamble.</h1>
          <p>Fixora connects Apple-device owners with a curated repair network, upfront pricing and a repair trail you can actually audit.</p>
          <div className="cta">
            <Link className="button primary" href="/book">Book a repair</Link>
            <Link className="button secondary" href="/dashboard">Track a repair</Link>
          </div>
          <div className="stats">
            <div className="stat"><strong>01</strong><span>Tell us what broke.</span></div>
            <div className="stat"><strong>02</strong><span>Approve the quote.</span></div>
            <div className="stat"><strong>03</strong><span>Keep the repair record.</span></div>
          </div>
        </div>
        <div className="card dark-card device-card">
          <div className="device-top"><span>Fixora Repair Passport</span><span className="live-dot">●</span></div>
          <div className="device-name">iPhone 15 Pro</div>
          <div className="device-status">Charging issue · Kisumu</div>
          <div className="passport-row"><span>Technician</span><b>Verified</b></div>
          <div className="passport-row"><span>Inspection</span><b>Recorded</b></div>
          <div className="passport-row"><span>Quote</span><b>Customer approved</b></div>
          <div className="passport-row"><span>Warranty</span><b>90 days</b></div>
          <div className="device-footer">Your device history stays with the device, not the shop.</div>
        </div>
      </section>

      <section className="section split-banner">
        <div><div className="eyebrow">The promise</div><h2>Convenience outside. Trust underneath.</h2></div>
        <p>Mobile repair when the job is suitable. Pickup for deeper work. Verified workshops for complex repairs.</p>
      </section>

      <section className="grid3 section">
        {trustItems.map(([title, body]) => <article className="card feature" key={title}><div className="feature-index">0{trustItems.findIndex(([item]) => item === title) + 1}</div><h3>{title}</h3><p>{body}</p></article>)}
      </section>

      <section className="section launch-card card">
        <div><div className="eyebrow">Kisumu pilot</div><h2>Starting narrow on purpose.</h2><p>iPhone screen, battery, charging, camera, audio and diagnostic requests are the first service set.</p></div>
        <Link className="button primary" href="/book">Start with your device</Link>
      </section>
    </Shell>
  );
}
