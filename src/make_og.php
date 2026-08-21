<?php

declare(strict_types=1);

/** Render the 1200x630 Open Graph cards for both languages. */

define('OUT', dirname(__DIR__) . '/site');

const W = 1200;
const H = 630;
const BG = '#0d0e0e';
const ACCENT = '#ebe4d2';
const MUTED = '#a69e92';
const FAINT = '#777064';
const LINE = '#7d7466';
const GRID = [125, 116, 102, 40];

const FONT_DIR = '/System/Library/Fonts/Supplemental/';
const BOLD = FONT_DIR . 'Arial Bold.ttf';
const REG = FONT_DIR . 'Arial.ttf';
const MONO = '/System/Library/Fonts/Menlo.ttc';

/**
 * GD asks for a point size and rasterises at 96 dpi; a font size in this file
 * means pixels, as it does everywhere else. 72/96 converts between the two.
 */
const PT_PER_PX = 0.75;

/** GD's alpha channel is 7-bit and inverted against the 8-bit alpha used here. */
function gd_alpha(int $alpha8): int
{
    return 127 - (int) round($alpha8 / 255 * 127);
}

/** @return array{int,int,int} */
function rgb(string $hex): array
{
    $n = (int) hexdec(ltrim($hex, '#'));

    return [($n >> 16) & 0xFF, ($n >> 8) & 0xFF, $n & 0xFF];
}

function colour(\GdImage $im, string $hex): int
{
    [$r, $g, $b] = rgb($hex);

    return imagecolorallocate($im, $r, $g, $b);
}

/**
 * Split one face out of a TrueType collection into a standalone font file.
 *
 * GD hands the path straight to FreeType with face index 0, so the only way to
 * reach Menlo Bold — face 1 of Menlo.ttc — is to write it out on its own. The
 * faces in a collection share their table data, so this copies the tables the
 * requested face points at and rewrites the directory offsets to match.
 */
function ttc_face(string $path, int $index): string
{
    $data = file_get_contents($path);
    if (substr($data, 0, 4) !== 'ttcf') {
        return $path;  // already a single-face file
    }

    $cache = sys_get_temp_dir() . '/'
        . pathinfo($path, PATHINFO_FILENAME) . '-' . $index . '-' . filemtime($path) . '.ttf';
    if (is_file($cache)) {
        return $cache;
    }

    $numFonts = unpack('N', $data, 8)[1];
    if ($index >= $numFonts) {
        fwrite(STDERR, "$path has $numFonts faces; no index $index\n");
        exit(1);
    }

    $dirOff = unpack('N', $data, 12 + 4 * $index)[1];
    $numTables = unpack('n', $data, $dirOff + 4)[1];

    $bodyOff = 12 + 16 * $numTables;
    $dir = '';
    $body = '';
    for ($i = 0; $i < $numTables; $i++) {
        $e = $dirOff + 12 + 16 * $i;
        $tag = substr($data, $e, 4);
        $checkSum = unpack('N', $data, $e + 4)[1];
        $offset = unpack('N', $data, $e + 8)[1];
        $length = unpack('N', $data, $e + 12)[1];

        $dir .= $tag . pack('NNN', $checkSum, $bodyOff + strlen($body), $length);
        $body .= substr($data, $offset, $length) . str_repeat("\0", (4 - $length % 4) % 4);
    }

    $entrySelector = (int) floor(log($numTables, 2));
    $searchRange = 16 * (2 ** $entrySelector);
    $header = substr($data, $dirOff, 4)
        . pack('nnnn', $numTables, $searchRange, $entrySelector, $numTables * 16 - $searchRange);

    file_put_contents($cache, $header . $dir . $body);

    return $cache;
}

/** A font at a pixel size, with the metrics the layout below needs. */
final class Font
{
    private readonly int $ascent;

    public function __construct(
        public readonly string $path,
        public readonly float $size,
    ) {
        $this->ascent = self::ascentPx($path, $size);
    }

    /**
     * Distance from the top of the text box down to the baseline.
     *
     * Positions in this file are top-left, as Pillow's default text anchor is;
     * GD draws from the baseline, so every y needs this added. FreeType rounds
     * the scaled hhea ascender up to whole pixels, so the same ceil is used.
     */
    private static function ascentPx(string $path, float $size): int
    {
        static $metrics = [];

        if (!isset($metrics[$path])) {
            $metrics[$path] = self::sfntMetrics($path);
        }
        [$unitsPerEm, $ascender] = $metrics[$path];

        return (int) ceil($ascender / $unitsPerEm * $size);
    }

    /** @return array{int,int} unitsPerEm and the hhea ascender, in font units */
    private static function sfntMetrics(string $path): array
    {
        $data = file_get_contents($path);
        $numTables = unpack('n', $data, 4)[1];
        $tables = [];
        for ($i = 0; $i < $numTables; $i++) {
            $e = 12 + 16 * $i;
            $tables[substr($data, $e, 4)] = unpack('N', $data, $e + 8)[1];
        }

        return [
            unpack('n', $data, $tables['head'] + 18)[1],
            unpack('n', $data, $tables['hhea'] + 4)[1],
        ];
    }

    public function width(string $text): float
    {
        if ($text === '') {
            return 0.0;
        }
        $box = imagettfbbox($this->size * PT_PER_PX, 0, $this->path, $text);

        return (float) ($box[2] - $box[0]);
    }

    public function draw(\GdImage $im, float $x, float $y, string $text, int $colour): void
    {
        imagettftext(
            $im,
            $this->size * PT_PER_PX,
            0,
            (int) round($x),
            (int) round($y) + $this->ascent,
            $colour,
            $this->path,
            $text,
        );
    }
}

/** @return list<string> */
function wrap(Font $font, string $text, float $maxWidth): array
{
    $lines = [];
    $line = '';
    foreach (preg_split('/\s+/u', trim($text), -1, PREG_SPLIT_NO_EMPTY) as $word) {
        $probe = trim($line . ' ' . $word);
        if ($font->width($probe) <= $maxWidth || $line === '') {
            $line = $probe;
        } else {
            $lines[] = $line;
            $line = $word;
        }
    }
    if ($line !== '') {
        $lines[] = $line;
    }

    return $lines;
}

function upper(string $text): string
{
    return mb_strtoupper($text, 'UTF-8');
}

/** @param list<array{string,string}> $cells */
function build(
    string $name,
    string $kicker,
    string $title,
    string $subtitle,
    string $footerRight,
    float $titleSize,
    array $cells,
    string $footerLeft = '66TON99.ORG.UA/AWG-TO-AMPS',
): void {
    $img = imagecreatetruecolor(W, H);
    imagealphablending($img, false);
    imagefilledrectangle($img, 0, 0, W - 1, H - 1, colour($img, BG));

    // The grid is drawn on its own transparent layer and composited once, so
    // the crossings come out the same shade as the lines rather than doubling.
    $grid = imagecreatetruecolor(W, H);
    imagealphablending($grid, false);
    imagesavealpha($grid, true);
    imagefilledrectangle($grid, 0, 0, W - 1, H - 1, imagecolorallocatealpha($grid, 0, 0, 0, 127));
    $gridColour = imagecolorallocatealpha($grid, GRID[0], GRID[1], GRID[2], gd_alpha(GRID[3]));
    for ($x = 0; $x < W; $x += 54) {
        imageline($grid, $x, 0, $x, H, $gridColour);
    }
    for ($y = 0; $y < H; $y += 54) {
        imageline($grid, 0, $y, W, $y, $gridColour);
    }
    imagealphablending($img, true);
    imagecopy($img, $grid, 0, 0, 0, 0, W, H);

    $accent = colour($img, ACCENT);
    $muted = colour($img, MUTED);
    $faint = colour($img, FAINT);
    $line = colour($img, LINE);

    $pad = 70;
    $mono = ttc_face(MONO, 0);
    $monoBold = ttc_face(MONO, 1);
    $fKick = new Font($mono, 19);
    $fTitle = new Font(BOLD, $titleSize);
    $fSub = new Font(REG, 25);
    $fCellLabel = new Font($mono, 15);
    $fCellValue = new Font($monoBold, 33);
    $fFoot = new Font($mono, 18);

    $y = 64;
    $fKick->draw($img, $pad, $y, upper($kicker), $muted);
    $y += 46;

    foreach (wrap($fTitle, $title, W - 2 * $pad - 40) as $text) {
        $fTitle->draw($img, $pad, $y, $text, $accent);
        $y += (int) ($titleSize * 0.98);
    }

    $y += 18;
    foreach (wrap($fSub, $subtitle, 900) as $text) {
        $fSub->draw($img, $pad, $y, $text, $muted);
        $y += 36;
    }

    // data strip
    $top = 432;
    $bottom = 520;
    imagerectangle($img, $pad, $top, W - $pad, $bottom, $line);
    $cellW = (W - 2 * $pad) / count($cells);
    foreach (array_values($cells) as $i => [$label, $value]) {
        $cx = $pad + $i * $cellW;
        if ($i) {
            imageline($img, (int) round($cx), $top, (int) round($cx), $bottom, $line);
        }
        $fCellLabel->draw($img, $cx + 22, $top + 18, upper($label), $faint);
        $fCellValue->draw($img, $cx + 22, $top + 42, $value, $accent);
    }

    // footer
    $fy = 566;
    imageline($img, $pad, $fy, W - $pad, $fy, $line);
    $fFoot->draw($img, $pad, $fy + 20, upper($footerLeft), $faint);
    $right = upper($footerRight);
    $fFoot->draw($img, W - $pad - $fFoot->width($right), $fy + 20, $right, $faint);

    $path = OUT . '/' . $name;
    imagesavealpha($img, false);
    imagepng($img, $path, 9);

    printf("%s  (%d, %d)  %s bytes\n", $name, W, H, number_format(filesize($path)));
}


const CELLS = [['4 AWG', '21.15 mm²'], ['60 °C', '62 A'], ['200 °C', '131 A'], ['0 AWG', '112 A']];

build(
    'og-awg-to-amps.png',
    'Wire sizing / 30—0 AWG · copper',
    'AWG to amps chart & calculator',
    'Real copper cross-section in mm², ampacity at 60 °C and 200 °C, strand-count '
    . 'calculator, bundle derating and DC voltage drop.',
    '17 gauges',
    76,
    CELLS,
);

const HOME_CELLS = [
    ['Stack', 'web / linux'],
    ['Cloud', 'OCI / NixOS'],
    ['Tools', 'AWG → A'],
    ['Profiles', '5'],
];

build(
    'og-home.png',
    '66ton99.org.ua',
    'Profiles and engineering references',
    'Personal index — profile links plus an AWG to amps chart and wire gauge '
    . 'ampacity calculator.',
    'personal index',
    68,
    HOME_CELLS,
    footerLeft: '66ton99.org.ua',
);

build(
    'og-home-uk.png',
    '66ton99.org.ua',
    'Профілі та інженерні довідники',
    'Персональний індекс — посилання на профілі, таблиця AWG в ампери й '
    . 'калькулятор перерізу дроту.',
    'персональний індекс',
    62,
    [['Стек', 'web / linux'], ['Хмара', 'OCI / NixOS'], ['Інструменти', 'AWG → А'], ['Профілі', '5']],
    footerLeft: '66ton99.org.ua/uk',
);

build(
    'og-awg-to-amps-uk.png',
    'Переріз дроту / 30—0 AWG · мідь',
    'AWG в ампери: таблиця і калькулятор',
    'Реальний переріз міді в мм², допустимий струм за 60 °C і 200 °C, калькулятор '
    . 'жилок, поправка на пучок і падіння напруги.',
    '17 калібрів',
    66,
    CELLS,
);
