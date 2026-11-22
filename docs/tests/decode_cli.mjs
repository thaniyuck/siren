// Used by encoder/tests/test_js_decoder.py: decode digits with the real viewer code.
//   node docs/tests/decode_cli.mjs <digits>
import { decodeFragment } from "../decode.js";

try {
  console.log(JSON.stringify(await decodeFragment(process.argv[2])));
} catch (err) {
  console.log(JSON.stringify({ error: err.code || "unknown", message: err.message }));
}
