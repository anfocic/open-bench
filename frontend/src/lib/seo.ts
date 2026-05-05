import {
  seoSite,
  seoPages,
  seoTemplates,
  type StaticPageKey,
  type TemplateKey,
  type JsonLdKey,
} from '../config/seo';

export interface SeoProps {
  title: string;
  description: string;
  ogImage: string;
  ogImageAlt: string;
  ogType: 'website' | 'article';
  canonicalPath: string;
  jsonLd: readonly JsonLdKey[];
  jsonLdData?: Record<string, unknown>;
  publishedTime?: string;
  prevPath?: string;
  nextPath?: string;
  noindex?: boolean;
}

type Vars = Record<string, string | number | undefined>;

function interp(tpl: string, vars: Vars): string {
  return tpl.replace(/\{(\w+)\}/g, (_, k) => {
    const v = vars[k];
    return v === undefined || v === null ? '' : String(v);
  });
}

export function pageSeo(
  key: StaticPageKey,
  canonicalPath: string,
  jsonLdData?: Record<string, unknown>,
): SeoProps {
  const cfg = seoPages[key];
  return {
    title: cfg.title,
    description: cfg.description,
    ogImage: cfg.ogImage,
    ogImageAlt: cfg.ogImageAlt ?? seoSite.defaultOgImageAlt,
    ogType: 'website',
    canonicalPath,
    jsonLd: cfg.jsonLd,
    jsonLdData,
  };
}

export function templateSeo(
  template: TemplateKey,
  canonicalPath: string,
  vars: Vars,
  jsonLdData?: Record<string, unknown>,
  publishedTime?: string,
  nav?: { prevPath?: string; nextPath?: string },
): SeoProps {
  const cfg = seoTemplates[template];
  const fullVars: Vars = { brandSuffix: seoSite.brandSuffix, ...vars };
  return {
    title: interp(cfg.titleTpl, fullVars),
    description: interp(cfg.descTpl, fullVars),
    ogImage: interp(cfg.ogTpl, fullVars),
    ogImageAlt: cfg.ogAltTpl ? interp(cfg.ogAltTpl, fullVars) : seoSite.defaultOgImageAlt,
    ogType: cfg.ogType,
    canonicalPath,
    jsonLd: cfg.jsonLd,
    jsonLdData,
    publishedTime,
    prevPath: nav?.prevPath,
    nextPath: nav?.nextPath,
  };
}

export { seoSite };
