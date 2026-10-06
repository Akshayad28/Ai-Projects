import { NextRequest, NextResponse } from 'next/server';
import { compareProductsServer } from '@/server/comparison';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function GET(req: NextRequest) {
  try {
    const searchParams = req.nextUrl.searchParams;
    const idsParam = searchParams.get('ids') || '';
    const ids = idsParam.split(',').map((s) => s.trim()).filter(Boolean);

    if (ids.length === 0) {
      return NextResponse.json(
        { detail: 'No product IDs provided. Specify ?ids=id1,id2' },
        { status: 400 }
      );
    }

    const comparison = await compareProductsServer(ids);
    return NextResponse.json(comparison);
  } catch (error: any) {
    console.error('[API GET /api/products/compare] Unhandled error:', error);
    return NextResponse.json(
      { detail: error.message || 'Comparison failed' },
      { status: 500 }
    );
  }
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const productIds: string[] = body.product_ids || [];

    if (!Array.isArray(productIds) || productIds.length === 0) {
      return NextResponse.json(
        { detail: 'Field product_ids is required and must be a non-empty array.' },
        { status: 400 }
      );
    }

    const comparison = await compareProductsServer(productIds);
    return NextResponse.json(comparison);
  } catch (error: any) {
    console.error('[API POST /api/products/compare] Unhandled error:', error);
    return NextResponse.json(
      { detail: error.message || 'Comparison failed' },
      { status: 500 }
    );
  }
}
