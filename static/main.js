document.addEventListener("DOMContentLoaded", () => {
  const goButton = document.getElementById("go-button");
  const status = document.getElementById("status");

  if (!goButton || !status) return;

  goButton.addEventListener("click", () => {
    status.textContent = "Поехали! Сигнал отправлен.";
    goButton.classList.remove("go-button--error");
    goButton.classList.add("go-button--success");
  });
});
