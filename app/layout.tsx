import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RainDrop Commander - AI Rule Supervisor",
  description: "Supervise and audit RainDrop Sentry rules before deployment",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}

