import path from "path";
import { Client } from "../src/fs";

const _DIR_TEST_DATA = path.join(__dirname, "../data/figma-community-archives");

const client = Client({
  paths: {
    files: _DIR_TEST_DATA,
    images: _DIR_TEST_DATA,
  },
});

test("get file", async () => {
  const { data } = await client.file("816744180312298871");
  expect(data).toHaveProperty("document");
});

// test("export image", async () => {
//   const nodeid = "51:2";
//   const { data } = await client.fileImages("816744180312298871", {
//     format: "png",
//     scale: 1,
//     ids: [nodeid],
//   });
//   expect(data).toHaveProperty("images");
//   console.log(data);

//   // pass this tets
//   expect(1).toBe(1);
// });

// test("image fills", async () => {
//   const { data } = await client.fileImageFills("816744180312298871");
//   expect(data).toHaveProperty("meta");
//   console.log(data);

//   // pass this tets
//   expect(1).toBe(1);
// });
