<?php

declare(strict_types=1);

/**
 * One-shot: turn the hand-written site/index.html into src/template-home.html.
 *
 * Kept in the repo so the transformation is auditable, but it only needs to run
 * again if the homepage design is rewritten from scratch.
 */

$here = __DIR__;
$src = file_get_contents(dirname(__DIR__) . '/site/index.html');
$out = $here . '/template-home.html';

if (file_exists($out) && !in_array('--force', $argv, true)) {
    fwrite(STDERR, basename($out) . " already exists; pass --force to regenerate\n");
    exit(1);
}

/** Replace exactly $count matches, or stop with an error naming the pattern. */
function sub(string $pattern, string $repl, int $count = 1): void
{
    global $src;

    $n = 0;
    // preg_replace treats $ and \ in the replacement as backreferences, so the
    // literal replacements below go through a callback instead.
    $src = preg_replace_callback($pattern, static fn (): string => $repl, $src, $count, $n);
    if ($n !== $count) {
        fwrite(STDERR, "expected $count replacement(s), made $n: " . substr($pattern, 0, 70) . "\n");
        exit(1);
    }
}

// ---- head ----------------------------------------------------------------
sub('/<html lang="en">/', '<html lang="{{LANG}}">');
sub(
    '/<meta\s+name="description"\s+content="[^"]*"\s*\/>/s',
    '<meta name="description" content="{{DESC}}" />'
);
sub('/<title>[^<]*<\/title>/', '<title>{{TITLE}}</title>');
sub(
    '/<link rel="canonical" href="[^"]*" \/>/',
    '<link rel="canonical" href="{{CANONICAL}}" />' . "\n"
    . '    <link rel="alternate" hreflang="en" href="https://66ton99.org.ua/" />' . "\n"
    . '    <link rel="alternate" hreflang="uk" href="https://66ton99.org.ua/uk" />' . "\n"
    . '    <link rel="alternate" hreflang="x-default" href="https://66ton99.org.ua/" />'
);
sub(
    '/<meta property="og:title" content="[^"]*" \/>/',
    '<meta property="og:title" content="{{TITLE}}" />'
);
sub(
    '/<meta property="og:description" content="[^"]*" \/>/',
    '<meta property="og:description" content="{{DESC}}" />'
);
sub(
    '/<meta property="og:url" content="[^"]*" \/>/',
    '<meta property="og:url" content="{{CANONICAL}}" />'
);
sub(
    '/<meta property="og:locale" content="[^"]*" \/>/',
    '<meta property="og:locale" content="{{OG_LOCALE}}" />' . "\n"
    . '    <meta property="og:locale:alternate" content="{{OG_LOCALE_ALT}}" />' . "\n"
    . '    <meta property="og:image" content="{{OG_IMAGE}}" />' . "\n"
    . '    <meta property="og:image:width" content="1200" />' . "\n"
    . '    <meta property="og:image:height" content="630" />' . "\n"
    . '    <meta property="og:image:type" content="image/png" />' . "\n"
    . '    <meta property="og:image:alt" content="{{OG_IMAGE_ALT}}" />' . "\n"
    . '    <meta name="twitter:card" content="summary_large_image" />' . "\n"
    . '    <meta name="twitter:title" content="{{TITLE}}" />' . "\n"
    . '    <meta name="twitter:description" content="{{DESC}}" />' . "\n"
    . '    <meta name="twitter:image" content="{{OG_IMAGE}}" />'
);

// ---- css: the img gets width/height attributes below, and height="620" is a
// presentational hint that would pin the box and make aspect-ratio inert ------
sub(
    "/      \.visual \{\n        width: 100%;\n/",
    "      .visual {\n        width: 100%;\n        height: auto;\n"
);
sub("/        object-fit: cover;\n/", "        object-fit: contain;\n");

// ---- css: h1 brand must look exactly like the old span, plus lang switch ---
sub(
    "/      \.brand \{\n        display: inline-flex;/",
    "      .brand {\n"
    . "        margin: 0;\n"
    . "        font-size: inherit;\n"
    . '        display: inline-flex;'
);
sub(
    "/      \.main \{\n        display: grid;/",
    "      .langswitch {\n"
    . "        display: inline-flex;\n"
    . "        align-items: center;\n"
    . "        gap: 7px;\n"
    . "      }\n\n"
    . "      .langswitch a,\n"
    . "      .langswitch span {\n"
    . "        padding: 3px 7px;\n"
    . "        border: 1px solid var(--line);\n"
    . "        color: var(--quiet);\n"
    . "      }\n\n"
    . "      .langswitch [aria-current=\"true\"] {\n"
    . "        border-color: var(--line-strong);\n"
    . "        color: var(--text);\n"
    . "      }\n\n"
    . "      .main {\n        display: grid;"
);

// ---- body ----------------------------------------------------------------
sub(
    '/<header class="top" aria-label="Site header">.*?<\/header>/s',
    '<header class="top" aria-label="{{A_HEADER}}">' . "\n"
    . '        <h1 class="brand">66Ton99</h1>' . "\n"
    . '        <nav class="langswitch" aria-label="{{A_LANG}}">{{LANG_LINKS}}</nav>' . "\n"
    . '      </header>'
);
sub('/<section class="main" aria-label="[^"]*">/', '<section class="main" aria-label="{{A_MAIN}}">');
sub('/<section aria-label="Visual profile">/', '<section aria-label="{{A_VISUAL}}">');
sub(
    '/<img class="visual" src="data:image\/svg\+xml;base64,[^"]+" alt="[^"]*" \/>/s',
    '<img class="visual" width="900" height="620" '
    . 'src="data:image/svg+xml;base64,{{SYSTEM_MAP}}" alt="{{SVG_ALT}}" />'
);
sub('/<aside class="links" aria-label="Social profiles">/', '<aside class="links" aria-label="{{A_PROFILES}}">');
sub('/<span>Profiles<\/span>/', '<span>{{T_PROFILES}}</span>');
sub('/<span>Open<\/span>/', '<span>{{OPEN}}</span>', 5);
sub(
    '/<aside class="links" aria-label="Tools and references">.*?<\/aside>/s',
    '<aside class="links" aria-label="{{A_TOOLS}}">' . "\n"
    . "          <header>\n"
    . "            <span>{{T_TOOLS}}</span>\n"
    . "            <span>{{N_TOOLS}}</span>\n"
    . "          </header>\n"
    . '          <ul class="link-list">' . "\n"
    . "{{TOOLS_LIST}}\n"
    . "          </ul>\n"
    . '        </aside>'
);
sub(
    '/<footer class="foot">.*?<\/footer>/s',
    '<footer class="foot">' . "\n"
    . "        <span>66Ton99</span>\n"
    . "        <span>{{FOOTER_R}}</span>\n"
    . '      </footer>'
);

file_put_contents($out, $src);
preg_match_all('/\{\{([A-Z_0-9]+)\}\}/', $src, $matches);
$tokens = array_unique($matches[1]);
sort($tokens, SORT_STRING);
printf("wrote %s with %d tokens:\n", basename($out), count($tokens));
echo '  ' . implode(', ', $tokens) . "\n";
