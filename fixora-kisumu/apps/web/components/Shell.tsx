import Link from "next/link";
import { Brand } from "./Brand";

export function Shell({ children }: { children: React.ReactNode }) {
  return (
    <main className="shell">
      <nav className="nav">
        <Link href="/" aria-label="Fixora home"><Brand /></Link>
        <div className="navlinks">
          <Link href="/book">Book repair</Link>
          <Link href="/dashboard">My repairs</Link>
          <Link href="/technician">Technician</Link>
          <Link href="/admin">Trust center</Link>
        </div>
      </nav>
      {children}
      <footer className="footer">
        <span>Fixora Kisumu</span>
        <span>Independent repair marketplace</span>
        <span>Credential labels are verification states, not Apple endorsements.</span>
      </footer>
    </main>
  );
}
