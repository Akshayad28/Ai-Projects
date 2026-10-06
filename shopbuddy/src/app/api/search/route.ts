import { NextRequest, NextResponse } from 'next/server';
import { orchestrateSearch } from '@/server/searchOrchestrator';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const {
      query = '',
      country = 'IN',
      currency = 'INR',
      sort_by = 'recommended',
      page = 1,
      page_size = 24,
    } = body;

    if (!query || typeof query !== 'string' || !query.trim()) {
      return NextResponse.json(
        { detail: 'Query parameter is required and cannot be empty.' },
        { status: 400 }
      );
    }

    const response = await orchestrateSearch(
      query.trim(),
      country,
      currency,
      sort_by,
      Number(page) || 1,
      Number(page_size) || 24
    );

    return NextResponse.json(response);
  } catch (error: any) {
    console.error('[API /api/search] Unhandled error:', error);
    return NextResponse.json(
      { detail: 'Internal search engine error. Please try again.' },
      { status: 500 }
    );
  }
}
