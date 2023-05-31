# `@figma-api/community` - Figma Community Data API

Figma Community API provide publicly available figma community files data, you can fetch file, images like it is yours. It also follows the same interface as our [Figma REST API Client - `@figma-api/rest`](https://github.com/gridaco/design-sdk) so you can easily switch between them without any code changes (very few changes).

## Installation

```sh
# npm
npm install --save @figma-api/community axios

# yarn
yarn add @figma-api/community axios
```

_Note_ - `axios` is a peer dependency, you need to install it as well.

## Usage

```ts
import { Client } from "@figma-api/community";

const client = Client();

// a file id is a id from figma.com/community/file/:id
// e.g. - https://www.figma.com/community/file/1035203688168086460
const fileid = "1035203688168086460";

// fetch file
const { data: document } = await client.file(fileid);

// fetch node images (export as images)
```

## About Images

Since the images are pre-exported and archived, we support limited `scale` of images, other wise, it will return 404.

**image scales**

- 1x (`1`)
- 2x (`2`)
- 3x (`3`)

**Downsized image fills**

The image fills are optimized to max 3mb per file (which still has great quality), you should use the node's width and height data to render the image fill as the actual size.
