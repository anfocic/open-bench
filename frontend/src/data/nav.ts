export interface NavLink {
  href: string;
  label: string;
  external?: boolean;
}

export const navLinks: NavLink[] = [
  { href: '/', label: 'home' },
  { href: '/about', label: 'about' },
  { href: '/model-royale', label: 'model royale' },
  { href: '/task/sandbox', label: 'task' },
  { href: 'https://github.com/anfocic/open-bench', label: 'github', external: true },
];