export interface NavLink {
  href: string;
  label: string;
}

export const navLinks: NavLink[] = [
  { href: '/round', label: 'rounds' },
  { href: '/notes', label: 'writeups' },
  { href: '/leaderboard', label: 'leaderboard' },
  { href: '/about', label: 'about' },
  { href: '/model-royale', label: 'model royale' },
];