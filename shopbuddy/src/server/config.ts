/**
 * Server-side configuration loader for Vercel Serverless Functions.
 * Never leaks secrets to the client browser.
 */

export const serverConfig = {
  get geminiApiKey(): string {
    return process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY || '';
  },
  get geminiModel(): string {
    return process.env.GEMINI_MODEL || 'gemini-flash-latest';
  },
  get firecrawlApiKey(): string {
    return process.env.FIRECRAWL_API_KEY || '';
  },
  get firecrawlEnabled(): boolean {
    return process.env.FIRECRAWL_ENABLED !== 'false';
  },
  get isDemoMode(): boolean {
    // Strictly false in production
    return false;
  },
  get environment(): string {
    return process.env.NODE_ENV || 'production';
  },
};
