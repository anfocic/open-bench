export interface NavLink {
  href: string;
  label: string;
  external?: boolean;
}

export const navLinks: NavLink[] = [
  { href: '/round', label: 'rounds' },
  { href: '/leaderboard', label: 'leaderboard' },
  { href: '/about', label: 'about' },
  { href: '/model-royale', label: 'model royale' },
  { href: 'https://github.com/anfocic/open-bench', label: 'github', external: true },
];