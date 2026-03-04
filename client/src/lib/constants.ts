export const GRADE_COLORS: Record<string, string> = {
  "A+": "text-emerald-600 bg-emerald-50 border-emerald-200",
  A: "text-emerald-600 bg-emerald-50 border-emerald-200",
  B: "text-blue-600 bg-blue-50 border-blue-200",
  C: "text-yellow-600 bg-yellow-50 border-yellow-200",
  D: "text-orange-600 bg-orange-50 border-orange-200",
  F: "text-red-600 bg-red-50 border-red-200",
};

export const SEVERITY_COLORS: Record<string, string> = {
  critical: "text-red-700 bg-red-50 border-red-200",
  warning: "text-yellow-700 bg-yellow-50 border-yellow-200",
  info: "text-blue-700 bg-blue-50 border-blue-200",
};

export const CATEGORY_COLORS: Record<string, string> = {
  "Blocking Prevention": "bg-blue-500",
  "Structured Data": "bg-purple-500",
  Discoverability: "bg-green-500",
};
