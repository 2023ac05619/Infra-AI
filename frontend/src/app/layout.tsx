import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Toaster } from "@/components/ui/toaster";
import { ThemeProvider } from "next-themes";
import { AuthProvider } from "@/components/providers/auth-provider";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "InfraChat - AI Infrastructure Assistant",
  description: "AI-powered infrastructure assistant with dynamic panes for commands and credentials",
  keywords: ["InfraChat", "AI", "Infrastructure", "DevOps", "Next.js", "TypeScript"],
  authors: [{ name: "InfraChat Team" }],
  icons: {
    icon: "/icon.svg",
  },
  openGraph: {
    title: "InfraChat - AI Infrastructure Assistant",
    description: "AI-powered infrastructure assistant with dynamic panes",
    url: "https://chat.z.ai",
    siteName: "InfraChat",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "InfraChat - AI Infrastructure Assistant",
    description: "AI-powered infrastructure assistant with dynamic panes",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning className="h-full">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-background text-foreground overflow-auto h-full`}
      >
        <AuthProvider>
          <ThemeProvider
            attribute="class"
            defaultTheme="system"
            enableSystem
            disableTransitionOnChange
          >
            {children}
            <Toaster />
          </ThemeProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
