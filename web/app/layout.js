import { Geist } from "next/font/google";
import "./globals.css";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import ChatWidget from "@/components/ChatWidget";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });

export const metadata = {
  title: "PulseFit Gym",
  description: "PulseFit Gym: group classes, personal training and flexible memberships. Ask Pulse, our support assistant.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className={`${geistSans.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col">
        <Header />
        <main className="flex-1">{children}</main>
        <Footer />
        <ChatWidget />
      </body>
    </html>
  );
}
