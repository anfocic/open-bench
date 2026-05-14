export interface NavLink {
  href: string;
  label: string;
}

export const navLinks: NavLink[] = [
  { href: '/about', label: 'about' },
  { href: '/benchmarks', label: 'benchmarks' },
  { href: '/writeups', label: 'writeups' },
];