import { NextResponse } from 'next/server';
import { serverConfig } from '@/server/config';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function GET() {
  return NextResponse.json({
    status: 'healthy',
    platform: 'vercel',
    demo_mode: serverConfig.isDemoMode,
    timestamp: new Date().toISOString(),
    providers: {
      google_scraper: {
        status: 'unavailable',
        reason: 'Playwright browser automation is unavailable in Vercel serverless environment; isolated scraper interface preserved for external worker compatibility',
      },
      firecrawl: {
        configured: Boolean(serverConfig.firecrawlApiKey),
        status: serverConfig.firecrawlApiKey ? 'configured' : 'unavailable',
      },
      gemini_ai: {
        configured: Boolean(serverConfig.geminiApiKey),
        model: serverConfig.geminiModel,
        status: serverConfig.geminiApiKey ? 'healthy' : 'unavailable',
      },
      catalog: {
        status: 'healthy',
        products_indexed: 692,
      },
    },
  });
}
