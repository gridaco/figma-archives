import { Client } from "../src/index";

const client = Client();

test("get file", async () => {
  const { data } = await client.file("767122733527420957");
  expect(data).toHaveProperty("document");
  // console.log(data);
});

test("get file nodes", async () => {
  const { data } = await client.fileNodes("767122733527420957", {
    ids: ["0:594"],
  });

  expect(data).toHaveProperty("nodes");
  expect(Object.keys(data.nodes)).toHaveLength(1);
  expect(data.nodes["0:594"]?.document.id).toBe("0:594");
});

test("export image", async () => {
  const nodeid = "0:594";
  const { data } = await client.fileImages("767122733527420957", {
    format: "png",
    scale: 1,
    ids: [nodeid],
  });
  expect(data).toHaveProperty("images");
  console.log(data);

  // pass this tets
  expect(1).toBe(1);
});

test("image fills", async () => {
  const { data } = await client.fileImageFills("767122733527420957");
  expect(data).toHaveProperty("meta");
  console.log(data);

  // pass this tets
  expect(1).toBe(1);
});
