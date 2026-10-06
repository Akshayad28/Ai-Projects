import { NextRequest, NextResponse } from 'next/server';
import { getPriceHistoryById } from '@/server/catalogService';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    if (!id) {
      return NextResponse.json({ detail: 'Product ID is required.' }, { status: 400 });
    }

    const priceHistory = getPriceHistoryById(id);
    return NextResponse.json(priceHistory);
  } catch (error: any) {
    console.error('[API /api/products/[id]/price-history] Unhandled error:', error);
    return NextResponse.json(
      { detail: 'Internal error retrieving price history.' },
      { status: 500 }
    );
  }
}
