# Spark Linux 覆盖率基础设施

此仓库独立构建 `ReallocAll/spark` 或 `EndstoneMC/spark` 的指定提交，执行 Linux 离线 CTest，生成 Cobertura XML、可离线浏览的详细 HTML 和诊断日志，并可上传到对应源仓库的 Codecov。不会修改或提交源仓库文件。

[2026-09-11 验证记录](VALIDATION.md)：个人仓库 72/72、组织仓库 29/29 测试通过，两者报告有效；个人上传已确认服务端处理和归属，组织上传仍需配置 `CODECOV_TOKEN_ENDSTONE` 后验证。

个人报告的 gcovr XML 行覆盖率为 73.55%，Codecov 为 49.49%：服务端移除部分行记录，并将分支未完全覆盖的命中行计为 partial、排除在分子之外。服务端全部文件与行已确认属于 XML 的 `src/` 集合；具体计数、公式及修正规则见验证记录。

覆盖范围是该 Linux 配置实际编译的 `src/` 实现及实例化的头文件代码，包括手写 proto；测试代码、Conan 和 FetchContent 依赖不计入报告。报告不代表 Windows、真实 BDS 或玩家交互场景覆盖率，也不表示未编译文件已被测量。

## 启动

在本仓库的 Settings → Secrets and variables → Actions 配置源仓库的 Codecov repository upload token：

| 源仓库 | Secret |
| --- | --- |
| `ReallocAll/spark` | `CODECOV_TOKEN` |
| `EndstoneMC/spark` | `CODECOV_TOKEN_ENDSTONE` |

上传模式会在构建前检查所选 secret 是否存在，缺失即失败，不会借用另一仓库 token。只生成 artifact 无需 token。构建 job 不接收任何 Codecov secret；上传在独立 runner 校验提交与报告后执行。

Actions → Linux coverage → Run workflow 的 **Branch** 选择基础设施版本；`source_repository` 和 `source_ref` 才选择待测源代码。默认源是 `ReallocAll/spark` 的 `develop`，上传开启。分支、标签和完整 40 位提交 SHA 都支持；重名分支与标签须使用 `refs/heads/` 或 `refs/tags/` 消歧。

```sh
# 默认个人仓库 develop，上传开启
gh workflow run coverage.yml --repo ReallocAll/spark-codecov --ref main
# 组织仓库 main，上传开启
gh workflow run coverage.yml --repo ReallocAll/spark-codecov --ref main -f source_repository=EndstoneMC/spark -f source_ref=main -F upload_to_codecov=true
# 组织仓库 main，只生成报告
gh workflow run coverage.yml --repo ReallocAll/spark-codecov --ref main -f source_repository=EndstoneMC/spark -f source_ref=main -F upload_to_codecov=false
gh run list --repo ReallocAll/spark-codecov --workflow coverage.yml
gh run download RUN_ID --repo ReallocAll/spark-codecov --dir reports
```

解压 artifact 后打开 `index.html`；下载整个 artifact 以保留详细页面。`coverage.xml` 是上传输入，`summary.json` 是覆盖率概要，`ctest.xml`、日志和 `metadata.json` 提供测试、工具版本、源 SHA、基础设施 SHA 和运行链接。Artifact 保留 14 天。

## 运行与归属

计划任务为 UTC `17 */6 * * *`，显式采用个人仓库 `develop`、上传开启。GitHub 可能延迟或丢弃高负载下的计划运行；公开仓库连续 60 天无活动可能停用计划任务，可在 Actions 页面重新启用。计划任务仅运行默认分支上的工作流。源仓库推送不会即时触发此仓库；本仓库 push/PR 仅运行轻量基础设施检查。

解析 job 先冻结源提交 SHA，构建与上传都检出该 SHA。Codecov 使用源仓库 slug 与源 SHA，分支使用真实分支名；标签使用 `refs/tags/<名称>`、直接 SHA 使用完整 SHA 作为独立报告归属标签，这些不声明存在同名 Git 分支。工作流不会伪造 PR。

上传 Action 成功说明请求成功提交，不等于服务端最终处理完成。可检查对应 Codecov 页面，或 `https://api.codecov.io/api/v2/github/{owner}/repos/spark/commits/{sha}/` 的提交身份与处理状态；本次实测提交状态为 `complete`；同一路径追加 `uploads/` 可检查上传状态 `merged`，并核对 `build_url` 指向当前 Actions 运行。正确 SHA、完成状态及本次运行的上传记录共同确认处理与归属，HTTP 200 或历史提交记录本身不足以确认。

## 构建约定与故障

Ubuntu 24.04 显式安装 LLVM/Clang 20、覆盖率 runtime、libc++20 和 libc++abi20，Python 3.12、CMake 3.31.10、Conan 2.32.0、gcovr 8.6。保留源仓库 Conan profile；仅消费者设为 Debug，依赖保留 RelWithDebInfo。外部 CMake hook 给 Spark 和离线测试目标添加 `--coverage -fprofile-update=atomic -O1 -g`，不会修改源 CMake 或测试断言。每次全新构建，不使用缓存。 Debug 构建使用低优化 `-O1`，审计每个插桩源码与测试编译命令最后生效的优化选项，并在 metadata 中记录 `coverage-optimization=-O1`。诊断表明 `-O0` 会暴露 ELF 测试对编译器地址加载方式的依赖，使已被 hook 的 GOT 值成为测试候选；`-O1` 保留该测试所需的原始指针，源代码与断言均未修改。优化可能改变行归属及合并代码，因此覆盖率仍需结合该构建模式解读。

构建会校验依赖配置、覆盖率目标和编译命令；CTest 测试数必须大于零，测试后必须产生 gcda。测试失败仍尝试生成报告，整体保持失败且不上传；失败日志也归档。任意历史或未来源 ref 可能不兼容当前工具链、preset 或测试布局，这会明确失败，需检查日志，不能据此断言源代码本身有缺陷。真实执行的测试数写入 metadata，不固定为某个版本的数量。

少数 gateway 共享库的 ELF 合约禁止启动与退出回调，与 gcov 运行时不兼容。[目标豁免策略](cmake/coverage-exemptions.json)仅对已审查的目标名称、类型、声明目录、完整源文件集合和显式 `-nostartfiles` 组合停止覆盖率注入；parser fixture 还必须声明 `SPARK_GATEWAY_PARSER_FIXTURE=1`。这些目标仍按源配置构建，所有测试与 ELF 校验照常执行，不移除编译或链接选项。未知目标或合约变化立即失败。

历史版本的五个 gateway 共享库各有一个未插桩的 `src/native/alloc/linux_allocation_gateway.cpp` 编译副本，因此该实现不被测量。当前源版本仅豁免 parser fixture 的两个测试编译命令，未插桩的 `src/` 实现命令数为零；生产 `spark_linux_permanent_gateway` 和测试 `spark_linux_gateway_test_backend` 静态目标仍插桩。同一源文件在其他普通目标中仍必须插桩；仅在豁免对象中实例化的头文件代码不被测量，不伪造零覆盖记录。Artifact 的 `coverage-exemptions.json` 及 metadata 记录实际豁免目标、原因、策略版本、实现命令的总数/插桩数/豁免数和未跳过测试的事实。

## 参考

- [GitHub workflow syntax](https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions)
- [GitHub schedule events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
- [LLVM APT packages](https://apt.llvm.org/)
- [CMake DEFER](https://cmake.org/cmake/help/latest/command/cmake_language.html#deferring-calls)
- [Conan settings patterns](https://docs.conan.io/2/reference/config_files/profiles.html)
- [gcovr Clang coverage](https://gcovr.com/en/stable/guide/compiling.html)
- [Codecov Action inputs](https://github.com/codecov/codecov-action)
- [actionlint releases](https://github.com/rhysd/actionlint/releases)

- [Clang 20 profile counter options](https://releases.llvm.org/20.1.0/tools/clang/docs/ClangCommandLineReference.html#cmdoption-clang-fprofile-update)
