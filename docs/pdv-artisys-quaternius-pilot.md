# MoneyPrint — PDV ArtiSys — Quaternius/Blender P2 (cena 05)

## Estado real

- **Implementado e testado em Python:** ponte para os modelos rigados Quaternius Universal Base Characters **[Standard]**, leitura do formato da biblioteca Universal Animation Library **[Standard]**, validação do esqueleto por nomes, seleção de animação real, instalação segura dos ZIPs CC0 e configuração da cena 05 com captura real do cardápio do PDV como textura MOVIE do Blender.
- **Não executado neste ambiente:** download dos ZIPs Standard (acesso externo bloqueado), importação dos assets no Blender (Blender indisponível), geração do arquivo `.blend` e renderização de MP4 3D. **Não afirme que a cena 05 foi renderizada.**
- **Sem fallback de PNG/boneco procedural.** O modo `quaternius_standard` para explicitamente caso os arquivos não estejam disponíveis.
- O projeto original `projects/pdv-artisys-blender-v1.json` foi preservado. O novo projeto está em `projects/pdv-artisys-quaternius-v1.json`. A `main`, os secrets, os workers e o release não foram alterados.

## Pacotes R$ 0 / CC0

1. [Universal Base Characters — Standard](https://quaternius.itch.io/universal-base-characters) — clique `Download Now` e `No thanks, just take me to the downloads`; baixe **Universal Base Characters[Standard].zip** (aprox. 122 MB). Não use Source ($19.99).
2. [Universal Animation Library — Standard](https://quaternius.itch.io/universal-animation-library) — mesmo processo, baixe **Universal Animation Library[Standard].zip** (aprox. 15 MB). Não use Pro ($9.99) nem Source ($14.99).

O site anuncia 120+ animações para o produto completo; o tier Standard gratuito contém cerca de 43 animações, verificadas em inventários públicos de arquivos. O piloto usa uma animação `Idle` real como base, com gestos adicionais em ossos do braço e cabeça em Blender. Não afirma ter animação de uso do celular pré-gravada no pack.

Links, licença e verificação: [Quaternius Base Characters](https://quaternius.com/packs/universalbasecharacters.html), [Quaternius Animation Library](https://quaternius.com/packs/universalanimationlibrary.html), licença CC0 1.0.

## Instalar ZIPs e validar

Na pasta raiz do pacote, com Python 3.11+:

```sh
python scripts/quaternius_assets.py \
  --characters-zip '/caminho/Universal Base Characters[Standard].zip' \
  --animations-zip '/caminho/Universal Animation Library[Standard].zip'
python scripts/build_blender.py --project projects/pdv-artisys-quaternius-v1.json --scene 05 --dry-run
python -m unittest discover -s tests -v
```

O instalador valida SHA-256 para versões conhecidas e protege contra extração fora do diretório. Se o distribuidor atualizar os ZIPs Standard, a verificação de hash falhará. Só depois de verificar a nova versão manualmente é permitido usar `--no-checksum` explicitamente; o controle de formato, nome Standard e licença permanece. Nunca há download/pagamento automático.

## Criar a cena-piloto no Blender (local / self-hosted)

Após baixar os dois ZIPs Standard e instalar Blender/FFmpeg, também existe o comando único, com QA automático:

```sh
python scripts/pilot_05.py --characters-zip '/caminho/Universal Base Characters[Standard].zip' --animations-zip '/caminho/Universal Animation Library[Standard].zip' --quality preview
```

Esse comando gera (se o Blender e os arquivos reais existirem) o `.blend`, o quadro de inspeção, o MP4 e o JSON de QA; **não publica**. No repositório GitHub, os scripts ficam em `scripts/blender_pdv/` em vez de `scripts/`.


Instale Blender 4.2+ (GPL), FFmpeg e rode:

```sh
blender -b --factory-startup --python scripts/build_blender.py -- \
  --project projects/pdv-artisys-quaternius-v1.json \
  --scene 05 --still --quality preview

blender -b --factory-startup --python scripts/build_blender.py -- \
  --project projects/pdv-artisys-quaternius-v1.json \
  --scene 05 --animate --quality preview
```

**Saídas esperadas, somente após execução real:** `outputs/pdv_artisys_scene_05.blend`, `..._still.png`, `..._05.mp4`. Cena 05: **210 frames, 7 segundos, 540 × 960** na qualidade preview, 30 fps. Os vídeos do sistema são externos aos arquivos de código do GitHub e devem ficar em `assets/` no executor privado. Render Full HD só após aprovar acting, enquadramento e nitidez.

Para render seletivo (sem renderizar as outras 11):

```sh
python scripts/render_and_join.py --project projects/pdv-artisys-quaternius-v1.json --quality preview --scene 05 --render
```

## Critérios de aprovação do piloto

- Pessoa 3D importada do `Regular_Female_FullBody.gltf` ou fallback verdadeiro de modelo da mesma biblioteca Standard; malha skinned ligada ao armature, **não** um sprite.
- Action importada do GLB da Universal Animation Library **Standard**; gesto local adicional para o celular, sem fingir que a biblioteca inclui uma animação de toque específica.
- Braços, mãos, cabeça e corpo movimentam-se de maneira coerente e não atravessam o dispositivo; corrigir rig e câmera no `.blend` se necessário.
- `SCREEN_REAL_PDV_05` contém a captura original `assets/cliente-qr.mp4` de 1080×1920, 30fps; texto legível sem textura substituta.
- Não há `source` humanoide de animação visível em render, placeholders, telões pretos ou timestamps errados.
- Não renderizar as outras 11 cenas nem mesclar na `main` antes de revisão visual do piloto.
