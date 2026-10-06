import { NextResponse } from 'next/server';
import { getCategoriesList } from '@/server/catalogService';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const categories = getCategoriesList();
    return NextResponse.json(categories);
  } catch (error: any) {
    console.error('[API /api/categories] Error:', error);
    return NextResponse.json([], { status: 500 });
  }
}
