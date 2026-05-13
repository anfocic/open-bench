export interface NavLink {
  href: string;
  label: string;
}

export const navLinks: NavLink[] = [
  { href: '/about', label: 'about' },
  { href: '/benchmarks', label: 'benchmarks' },
  { href: '/model-royale', label: 'model royale' },
];