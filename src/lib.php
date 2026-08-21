<?php

declare(strict_types=1);

/**
 * Shared helpers for the page generators.
 *
 * The generated pages are committed to site/ and CI fails if a rebuild changes
 * them, so every helper here exists to reproduce a specific formatting choice
 * byte for byte rather than to be merely equivalent.
 */

// json_encode leans on this for the shortest round-trip float representation,
// which is what makes 100.0 come out as "100.0" and 61.2 as "61.2". A php.ini
// that pins a fixed precision would quietly reformat every number in the page.
ini_set('serialize_precision', '-1');

/** Escape flags that make a PHP-encoded scalar match Python's json.dumps. */
const JSON_PY = JSON_UNESCAPED_UNICODE
    | JSON_UNESCAPED_SLASHES
    | JSON_UNESCAPED_LINE_TERMINATORS
    | JSON_PRESERVE_ZERO_FRACTION;

/**
 * Encode as json.dumps(..., ensure_ascii=False) does.
 *
 * json_encode alone is not enough: Python separates items with ", " and keys
 * from values with ": ", where PHP omits both spaces, and Python's pretty
 * printer indents by the width you ask for where JSON_PRETTY_PRINT is fixed at
 * four. Scalars still go through json_encode, so string escaping and float
 * formatting stay in C.
 *
 * @param int|null $indent Spaces per level, or null for the compact form.
 */
function json_py(mixed $value, ?int $indent = null, int $level = 0): string
{
    if (!is_array($value)) {
        return json_encode($value, JSON_PY | JSON_THROW_ON_ERROR);
    }

    $isList = array_is_list($value);
    [$open, $close] = $isList ? ['[', ']'] : ['{', '}'];

    if ($value === []) {
        return $open . $close;
    }

    $parts = [];
    foreach ($value as $key => $item) {
        $encoded = json_py($item, $indent, $level + 1);
        $parts[] = $isList
            ? $encoded
            : json_encode((string) $key, JSON_PY | JSON_THROW_ON_ERROR) . ': ' . $encoded;
    }

    if ($indent === null) {
        return $open . implode(', ', $parts) . $close;
    }

    $pad = str_repeat(' ', $indent * ($level + 1));
    $endPad = str_repeat(' ', $indent * $level);

    return $open . "\n" . $pad . implode(",\n" . $pad, $parts) . "\n" . $endPad . $close;
}

/**
 * Substitute {{TOKEN}} placeholders, then write the page out.
 *
 * A template token nobody filled in would ship to production as literal
 * braces, so an unreplaced one is a hard failure rather than a warning.
 *
 * @param array<string,string> $values
 */
function render_template(string $template, array $values, string $outPath, string $outRoot): void
{
    foreach ($values as $key => $value) {
        $template = str_replace('{{' . $key . '}}', $value, $template);
    }

    preg_match_all('/\{\{([A-Z_0-9]+)\}\}/', $template, $matches);
    $leftover = array_unique($matches[1]);
    if ($leftover !== []) {
        sort($leftover, SORT_STRING);
        fwrite(
            STDERR,
            'Unreplaced tokens in ' . basename($outPath) . ": ['" . implode("', '", $leftover) . "']\n"
        );
        exit(1);
    }

    write_file($outPath, $template);
    printf(
        "wrote %s  (%s bytes)\n",
        relative_to($outPath, $outRoot),
        number_format(strlen($template))
    );
}

/** Write a file, creating its directory first. */
function write_file(string $path, string $contents): void
{
    $dir = dirname($path);
    if (!is_dir($dir) && !mkdir($dir, 0o777, true) && !is_dir($dir)) {
        fwrite(STDERR, "cannot create directory $dir\n");
        exit(1);
    }
    file_put_contents($path, $contents);
}

/** Path relative to a directory, for build log lines. */
function relative_to(string $path, string $root): string
{
    $root = rtrim($root, '/') . '/';

    return str_starts_with($path, $root) ? substr($path, strlen($root)) : $path;
}
