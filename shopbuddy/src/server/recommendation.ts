import { RecommendationBreakdownDTO } from './types';

export function computeRecommendation(
  title: string,
  price: number | undefined,
  rating: number | undefined,
  reviewCount: number | undefined,
  budgetMax: number | undefined,
  offersCount: number = 1
): RecommendationBreakdownDTO {
  let score = 70;
  const reasons: string[] = [];
  const drawbacks: string[] = [];
  const whyNotHigher: string[] = [];

  // Rating impact
  if (rating && rating >= 4.5) {
    score += 15;
    reasons.push(`Outstanding user satisfaction (${rating.toFixed(1)}/5 stars)`);
  } else if (rating && rating >= 4.0) {
    score += 8;
    reasons.push(`Consistently positive verified reviews (${rating.toFixed(1)}/5 stars)`);
  } else if (rating && rating < 3.5) {
    score -= 10;
    drawbacks.push(`Below-average customer rating (${rating.toFixed(1)}/5 stars)`);
    whyNotHigher.push('User sentiment is mixed across major retailers');
  }

  // Review volume impact
  if (reviewCount && reviewCount > 500) {
    score += 8;
    reasons.push(`High confidence with extensive review volume (${reviewCount.toLocaleString()}+ reviews)`);
  } else if (!reviewCount || reviewCount < 15) {
    score -= 5;
    whyNotHigher.push('Limited review feedback available on major marketplaces');
  }

  // Price & Budget fit
  if (budgetMax && price) {
    if (price <= budgetMax) {
      const savings = Math.round(((budgetMax - price) / budgetMax) * 100);
      if (savings > 10) {
        score += 7;
        reasons.push(`Great value: ${savings}% below your maximum budget`);
      } else {
        reasons.push('Comfortably within target budget');
      }
    } else {
      score -= 15;
      drawbacks.push(`Priced above your specified budget ceiling`);
      whyNotHigher.push('Requires exceeding intended budget');
    }
  }

  // Multi-retailer competition
  if (offersCount > 1) {
    score += 5;
    reasons.push(`Available across multiple retailers (${offersCount} verified offers)`);
  }

  // Bound score between 40 and 99
  const finalScore = Math.max(45, Math.min(98, score));

  if (reasons.length === 0) {
    reasons.push('Meets essential search specifications');
  }

  return {
    match_score: finalScore,
    reasons,
    drawbacks,
    why_not_higher: whyNotHigher,
  };
}
