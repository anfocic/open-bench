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
  ogType: 'website' | 'article';
  canonicalPath: string;
  jsonLd: readonly JsonLdKey[];
  jsonLdData?: Record<string, unknown>;
  publishedTime?: string;
  noindex?: boolean;
}

type Vars = Record<string, string | number | undefined>;

function interp(tpl: string, vars: Vars): string {
  return tpl.replace(/\{(\w+)\}/g, (_, k) => {
    const v = vars[k];
    return v === undefined || v === null ? '' : String(v);
  });
}

export function pageSeo(key: StaticPageKey, canonicalPath: string): SeoProps {
  const cfg = seoPages[key];
  return {
    title: cfg.title,
    description: cfg.description,
    ogImage: cfg.ogImage,
    ogType: 'website',
    canonicalPath,
    jsonLd: cfg.jsonLd,
  };
}

export function templateSeo(
  template: TemplateKey,
  canonicalPath: string,
  vars: Vars,
  jsonLdData?: Record<string, unknown>,
  publishedTime?: string,
): SeoProps {
  const cfg = seoTemplates[template];
  const fullVars: Vars = { brandSuffix: seoSite.brandSuffix, ...vars };
  return {
    title: interp(cfg.titleTpl, fullVars),
    description: interp(cfg.descTpl, fullVars),
    ogImage: interp(cfg.ogTpl, fullVars),
    ogType: cfg.ogType,
    canonicalPath,
    jsonLd: cfg.jsonLd,
    jsonLdData,
    publishedTime,
  };
}

export { seoSite };
