export function campaignReadinessLabel(score: number): string {
  if (score === 0) return "Start by creating your first channel asset";
  if (score < 100) return "Resolve blockers to keep the campaign moving";
  return "Campaign is ready for approval and publishing";
}
export function validationMessage(error: unknown): string {
  void error;
  return "We kept your work. Check the API connection and try again.";
}
