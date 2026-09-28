import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata={title:"Fixora — Trusted repair in Kisumu",description:"Verified technicians, upfront quotes and repair history for Apple-device owners in Kisumu."};
export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="en"><body>{children}</body></html>}
