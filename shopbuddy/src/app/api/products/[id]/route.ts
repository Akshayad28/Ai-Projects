import { NextRequest, NextResponse } from 'next/server';
import { getProductById } from '@/server/catalogService';

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

    const product = getProductById(id);
    if (!product) {
      return NextResponse.json({ detail: 'Product not found.' }, { status: 404 });
    }

    return NextResponse.json(product);
  } catch (error: any) {
    console.error('[API /api/products/[id]] Unhandled error:', error);
    return NextResponse.json(
      { detail: 'Internal error retrieving product.' },
      { status: 500 }
    );
  }
}
