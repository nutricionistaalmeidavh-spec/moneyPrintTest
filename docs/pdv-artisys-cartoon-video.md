# PDV ArtiSys — animação ilustrada no MoneyPrint

Projeto com **12 cenas / 82 s / 720×1280 / 30 fps**. Core **R$ 0** com Pillow, NumPy e FFmpeg/FFprobe. Os tutoriais reais continuam intactos em `assets/pdv/`.

## Camadas

Cada cena possui: fundo cinematográfico, ilustrações dos seis personagens, rig 2D (cabeça e corpo independentes, sem sincronia labial), objetos de ação, mockup do dispositivo, captura real e tipografia. As capturas não são telas recriadas. Há um JSON editável em `projects/`.

## Executar

Instale Python 3.11+, Pillow e NumPy, além do FFmpeg/FFprobe. Depois execute na raiz:

```bash
python scripts/illustrated_video.py --prepare-only
python scripts/illustrated_video.py --only 7 --force
python scripts/illustrated_video.py
```

Para juntar cenas já renderizadas, use `--join-only`. O resultado fica em `outputs/MoneyPrint_PDV_Artisys_Cartoon_82s.mp4`. Para voltar a renderizar tudo, use `--force`. Não há publicação automática.

## Voz

O MP4 entregue possui trilha instrumental original e **não possui narração falada**. A voz brasileira Paradee-8M-PtBr não estava disponível localmente e não foi substituída por uma voz robótica. O texto de narração e o SRT estão neste pacote para sincronização posterior.

## Privacidade

As mídias reais da operação vêm dos tutoriais do Drive autorizados pelo proprietário e estão neste pacote privado, não no repositório GitHub público. Não colocar mídias privadas numa branch pública sem autorização explícita.

## Observações

Animação 2D estilizada: movimentos de cabeça, corpo e objetos; **não é animação facial/lip-sync ou caminhada quadro a quadro**. O vídeo é o primeiro corte visual para revisão, sem renderização final de voz.
