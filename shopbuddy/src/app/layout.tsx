import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import '@/styles/globals.scss';
import { Header } from '@/components/navigation/Header';
import { MobileNav } from '@/components/navigation/MobileNav';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  weight: ['400', '500'],
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'ShopBuddy AI — Search smarter. Compare everything. Buy with confidence.',
  description: 'Warm, illustrated personal shopping agent on cream paper. Search products, compare offers across retailers, analyze reviews, and find products you won’t regret buying.',
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_APP_URL ||
    (process.env.VERCEL_URL ? `https://${process.env.VERCEL_URL}` : 'http://localhost:3000')
  ),
  icons: {
    icon: [
      { url: '/icon.png', sizes: '32x32', type: 'image/png' },
      { url: '/logo.png', sizes: '1024x1024', type: 'image/png' },
    ],
    apple: [
      { url: '/apple-icon.png', sizes: '180x180', type: 'image/png' },
    ],
    shortcut: '/favicon.ico',
  },
  openGraph: {
    title: 'ShopBuddy AI — Personal Shopping Research Engine',
    description: "Don't just find the cheapest product. Find the product you are least likely to regret buying.",
    siteName: 'ShopBuddy AI',
    type: 'website',
    images: [
      {
        url: '/logo.png',
        width: 1024,
        height: 1024,
        alt: 'ShopBuddy AI Logo',
      },
    ],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={inter.variable} data-scroll-behavior="smooth">
      <body style={{ backgroundColor: '#f5f1e4', color: '#2c2e2a' }}>
        <Header />
        <main className="page-wrapper">{children}</main>
        <MobileNav />

        {/* MindMarket Sunshine Pop Footer Accent Band */}
        <footer style={{
          backgroundColor: '#f5e211',
          color: '#2c2e2a',
          padding: '60px 20px 84px 20px',
          textAlign: 'center',
          borderTop: '2px solid #2c2e2a',
          position: 'relative',
        }}>
          <div style={{ maxWidth: '880px', margin: '0 auto' }}>
            <div style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              backgroundColor: '#ffffff',
              borderRadius: '50px',
              padding: '8px 20px',
              marginBottom: '20px',
              border: '1px solid #2c2e2a',
              fontSize: '15px',
              fontWeight: 500,
            }}>
              <span style={{
                width: '10px',
                height: '10px',
                borderRadius: '50%',
                backgroundColor: '#8ed462',
                display: 'inline-block'
              }} />
              <span>MindMarket Verified Shopping Engine</span>
            </div>

            <h2
              style={{
                fontSize: 'clamp(32px, 4vw, 44px)',
                lineHeight: '1.15',
                fontWeight: 600,
                color: '#2c2e2a',
                margin: '0 auto 20px',
                letterSpacing: '-0.03em',
                textAlign: 'center',
                maxWidth: '780px',
                textWrap: 'balance',
              }}
            >
              Search smarter. Compare everything. Buy with confidence.
            </h2>

            <p style={{
              fontSize: '15px',
              lineHeight: '1.6',
              color: '#2c2e2a',
              maxWidth: '640px',
              margin: '0 auto 24px auto',
              fontWeight: 400,
            }}>
              ShopBuddy evaluates products objectively based on specifications, historical price observations, and verified customer feedback. Some retailer links may earn a commission. This never compromises product rankings or match scores.
            </p>

            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '24px',
              fontSize: '15px',
              fontWeight: 500,
              color: '#2c2e2a',
              flexWrap: 'wrap',
            }}>
              <span style={{ borderBottom: '1px solid #80827f', paddingBottom: '2px' }}>Independent Analysis</span>
              <span style={{ borderBottom: '1px solid #80827f', paddingBottom: '2px' }}>Zero Sponsored Bias</span>
              <span style={{ borderBottom: '1px solid #80827f', paddingBottom: '2px' }}>Multi-Retailer Pricing</span>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
