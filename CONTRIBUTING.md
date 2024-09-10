## Contributing

- Make a branch
- Submete um PR para ver se valida as mudanças
- Depois sobe um PR de release
- Faz o bumpversion no service que teve mudança de versão
- Cria uma tag com o nome <service_name>_v0.x.y
    - `git tag -a "airless-core_v0.1.0" -m "first tag"`
- Faz o push da tag com a nova versão do release
    - `git push origin --tags`
- Cada release traz apenas modificações de um service