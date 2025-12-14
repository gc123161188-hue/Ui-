
import argparse
from renderer import render

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--theme", default="theme_classic_v1.json")
    p.add_argument("--product", default="sample_product.json")
    p.add_argument("--out", default="out.png")
    args = p.parse_args()
    render(args.theme, args.product, args.out)
    print("OK ->", args.out)
