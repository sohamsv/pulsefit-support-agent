// Facts below come from PulseFit's help docs (made-up business, practice data).
export const PLANS = [
  { id: "monthly", name: "Monthly", price: "₹1,999", per: "per month", points: ["Gym floor access", "All group classes", "Auto-renews (turn off 2 days before renewal)", "Cancel before renewal"] },
  { id: "quarterly", name: "Quarterly", price: "₹5,499", per: "per quarter", highlight: true, points: ["Gym floor access", "All group classes", "Freeze up to 15 days", "Not refundable after 7 days"] },
  { id: "yearly", name: "Yearly", price: "₹17,999", per: "per year", points: ["Joining fee waived", "Use all PulseFit branches", "4 guest passes a year", "Freeze up to 45 days", "EMI with select banks"] },
];

export const CLASSES = [
  { name: "Zumba", blurb: "Dance-fitness party. High energy, big smiles, zero choreography stress.", level: "All levels", tag: "Cardio" },
  { name: "Yoga", blurb: "Mobility, balance and breath work to reset after a long week.", level: "All levels", tag: "Mind & body" },
  { name: "HIIT", blurb: "Short, hard intervals that torch calories and build stamina.", level: "Intermediate", tag: "Cardio" },
  { name: "Spin", blurb: "Rhythm-driven indoor cycling with hills, sprints and a playlist to match.", level: "All levels", tag: "Cardio" },
  { name: "Strength", blurb: "Coached lifting sessions to build strength safely and steadily.", level: "All levels", tag: "Strength" },
];

export const FAQS = [
  { q: "Is there a joining fee?", a: "Yes, a one-time ₹999 joining fee. It is waived on yearly plans." },
  { q: "What are the gym timings?", a: "5 AM to 11 PM on weekdays and 6 AM to 9 PM on weekends." },
  { q: "Can I take a free trial?", a: "Yes, one free 1-day pass per person. Book it in the app and bring a photo ID." },
  { q: "Can I freeze my membership?", a: "Yes. Quarterly plans can freeze up to 15 days and yearly plans up to 45 days, with 3 days' notice." },
  { q: "Can I transfer my membership to a friend?", a: "Yes, once, for ₹500, if more than 30 days are left." },
  { q: "Which payment methods are accepted?", a: "UPI, cards, and EMI on yearly plans with select banks." },
];

export const FACILITIES = [
  { title: "Lockers & showers", text: "Lockers are free for the day. Bring your own lock." },
  { title: "Parking", text: "Free two-wheeler parking. Car parking depends on the branch." },
  { title: "Quick check-in", text: "Scan the QR code at the entrance with the PulseFit app." },
  { title: "Personal training", text: "From ₹4,000 for 12 sessions, with a free first consultation." },
];

export const BRANCHES = ["Panjim", "Margao", "Mapusa"];

export const TIMINGS = [
  { days: "Monday to Friday", hours: "5 AM to 11 PM" },
  { days: "Saturday and Sunday", hours: "6 AM to 9 PM" },
];
